import os
import time
import re
import tempfile
import urllib.request
import urllib.error

import mouse
import screen
import template

VAR_PATTERN = re.compile(r'\{(\w+)\.(\w+)\}')


class ActionEngine:
    def __init__(self, config):
        self.context = {}
        self.monitors = screen.get_monitors()
        self.default_monitor = config.get('monitor', 1)
        self.template_dir = config.get('template_dir', 'templates')
        self._url_cache = {}
        self.keep_template = config.get('keep_template', False)
        
        if self.keep_template and not os.path.exists(self.template_dir):
            os.makedirs(self.template_dir, exist_ok=True)

    def _resolve(self, value):
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            def _replace(m):
                aid, field = m.group(1), m.group(2)
                ctx = self.context.get(aid, {})
                return str(ctx.get(field, m.group(0)))
            return VAR_PATTERN.sub(_replace, value)
        return value

    def _resolve_pos(self, action):
        try:
            x = self._resolve(action.get('x', 0))
            y = self._resolve(action.get('y', 0))
            return int(float(x)), int(float(y))
        except (ValueError, TypeError):
            print(f"[ERROR] Invalid coordinates: x={action.get('x')}, y={action.get('y')}")
            return 0, 0

    def _download_template(self, url: str, timeout: int = 30) -> str | None:
        """下载远程图片到临时文件或本地 templates 目录"""
        try:
            # 从 URL 生成文件名
            import hashlib
            url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
            filename = f'url_{url_hash}.png'
            local_path = os.path.join(self.template_dir, filename)
            
            # 优先检查本地是否已有缓存
            if self.keep_template and os.path.exists(local_path):
                print(f"[CACHE] 使用本地缓存：{local_path}")
                return local_path
            
            # 检查内存缓存
            if url in self._url_cache:
                if self.keep_template:
                    # 保存到本地目录
                    with open(local_path, 'wb') as f:
                        f.write(self._url_cache[url])
                    print(f"[SAVE] 保存到本地：{local_path}")
                    return local_path
                else:
                    fd, path = tempfile.mkstemp(suffix='.png')
                    os.write(fd, self._url_cache[url])
                    os.close(fd)
                    return path
            
            # 添加 User-Agent 和 Referer 头，避免被服务器拒绝
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Referer': 'https://' + url.split('/')[2] if url.startswith('https://') else 'http://' + url.split('/')[2]
            })
            
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status != 200:
                    print(f"[ERROR] URL 返回非 200 状态码：{url}, status={response.status}")
                    return None
                
                content_type = response.getheader('Content-Type', '')
                if not content_type.startswith('image/'):
                    print(f"[WARNING] URL 返回非图片内容：{url}, Content-Type={content_type}")
                
                data = response.read()
                self._url_cache[url] = data
                
                if self.keep_template:
                    # 保存到本地目录
                    with open(local_path, 'wb') as f:
                        f.write(data)
                    print(f"[SAVE] 保存到本地：{local_path}")
                    return local_path
                else:
                    fd, path = tempfile.mkstemp(suffix='.png')
                    os.write(fd, data)
                    os.close(fd)
                    return path
                
        except urllib.error.HTTPError as e:
            print(f"[ERROR] HTTP 错误：{url}, status={e.code}")
            return None
        except urllib.error.URLError as e:
            print(f"[ERROR] URL 错误：{url}, reason={e.reason}")
            return None
        except Exception as e:
            print(f"[ERROR] 下载失败：{url}, {e}")
            return None

    def _exec_recognize(self, action):
        template_path = self._resolve(action['template'])
        is_url = template_path.startswith(('http://', 'https://'))
        temp_file = None
        
        if is_url:
            timeout = int(action.get('download_timeout', 30))
            print(f"[DOWNLOAD] 从 URL 下载模板：{template_path}, timeout={timeout}s")
            temp_file = self._download_template(template_path, timeout)
            if temp_file is None:
                return {'found': False}
            template_path = temp_file
        
        if not os.path.isabs(template_path):
            template_path = os.path.join(self.template_dir, template_path)

        threshold = float(action.get('threshold', 0.8))
        monitor_idx = int(action.get('monitor', self.default_monitor))
        retry = float(action.get('retry_interval', 0))
        timeout = float(action.get('timeout', 0))

        try:
            tmpl = template.load(template_path)
            if tmpl is None:
                print(f"[ERROR] Load template failed: {template_path}")
                return {'found': False}

            template_gray, tw, th = tmpl
            start = time.time()

            while True:
                _, img_gray, mon = screen.capture_monitor(monitor_idx)
                match = template.find(img_gray, template_gray, tw, th, threshold)

                if match:
                    gx, gy = screen.to_global(mon, match['center_x'], match['center_y'])
                    return {
                        'found': True,
                        'center_x': gx,
                        'center_y': gy,
                        'confidence': match['confidence'],
                    }

                if timeout <= 0:
                    return {'found': False}

                if time.time() - start >= timeout:
                    print(f"[TIMEOUT] {template_path} not found within {timeout}s")
                    return {'found': False}

                time.sleep(retry)
        finally:
            # 仅在 keep_template=False 时删除临时文件
            if is_url and temp_file and os.path.exists(temp_file) and not self.keep_template:
                os.unlink(temp_file)

    def execute(self, action):
        atype = action['type']
        aid = action.get('id')
        result = None

        if atype == 'click':
            x, y = self._resolve_pos(action)
            btn = action.get('button', 'left')
            btn_label = '右键' if btn == 'right' else '左键'
            print(f"[CLICK] ({x}, {y}) {btn_label}")
            mouse.click(x, y, button=btn)

        elif atype == 'move':
            x, y = self._resolve_pos(action)
            print(f"[MOVE] → ({x}, {y})")
            mouse.move_to(x, y)

        elif atype == 'recognize':
            tpl = self._resolve(action.get('template', ''))
            print(f"[RECOGNIZE] 搜索模板: {tpl}")
            result = self._exec_recognize(action)
            if result.get('found'):
                print(f"  → ✓ 找到, 坐标=({result['center_x']}, {result['center_y']}), 置信度={result['confidence']:.2%}")
            else:
                print(f"  → ✗ 未找到")

        elif atype == 'wait':
            dur = action.get('duration', 1)
            print(f"[WAIT] {dur}秒")
            time.sleep(dur)

        elif atype == 'group':
            subs = action.get('actions', [])
            print(f"[GROUP] 开始执行 {len(subs)} 个子动作")
            for s in subs:
                self.execute(s)
            print(f"[GROUP] 完成")

        elif atype == 'loop':
            count = action.get('count', 1)
            interval = action.get('interval', 0)
            for i in range(count):
                print(f"[LOOP] 第 {i+1}/{count} 轮")
                for s in action.get('actions', []):
                    self.execute(s)
                if interval and i < count - 1:
                    time.sleep(interval)

        if aid and result is not None:
            self.context[aid] = result

        if atype == 'recognize':
            success = result.get('found', False) if result else False
            sub_actions = action.get('on_success' if success else 'on_failure', [])
            if isinstance(sub_actions, dict):
                sub_actions = [sub_actions]
            for sub in sub_actions:
                self.execute(sub)
