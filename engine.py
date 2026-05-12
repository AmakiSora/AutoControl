import os
import time
import re

import mouse
import screen
import template

VAR_PATTERN = re.compile(r'\{(\w+)\.(\w+)\}')


class ActionEngine:
    def __init__(self, config):
        self.context = {}
        self.monitors = screen.get_monitors()
        self.default_monitor = config.get('monitor', 1)
        self.template_dir = config.get('template_dir', '')

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

    def _exec_recognize(self, action):
        template_path = self._resolve(action['template'])
        if not os.path.isabs(template_path):
            template_path = os.path.join(self.template_dir, template_path)

        threshold = float(action.get('threshold', 0.8))
        monitor_idx = int(action.get('monitor', self.default_monitor))
        retry = float(action.get('retry_interval', 0))
        timeout = float(action.get('timeout', 0))

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

    def execute(self, action):
        atype = action['type']
        aid = action.get('id')
        result = None
        stop_on_failure = action.get('stop_on_failure', False)

        if atype == 'click':
            x, y = self._resolve_pos(action)
            btn = action.get('button', 'left')
            mouse.click(x, y, button=btn)

        elif atype == 'move':
            x, y = self._resolve_pos(action)
            mouse.move_to(x, y)

        elif atype == 'recognize':
            result = self._exec_recognize(action)

        elif atype == 'wait':
            time.sleep(action.get('duration', 1))

        elif atype == 'log':
            print(self._resolve(action.get('message', '')))

        elif atype == 'group':
            for sub in action.get('actions', []):
                self.execute(sub)

        elif atype == 'loop':
            count = action.get('count', 1)
            interval = action.get('interval', 0)
            for i in range(count):
                print(f"[LOOP] {i + 1}/{count}")
                for sub in action.get('actions', []):
                    self.execute(sub)
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
