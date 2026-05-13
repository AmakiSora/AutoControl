# autoControl — 多显示器屏幕监控与图像识别自动化

基于屏幕截图与图像模板匹配的 Windows GUI 自动化工具。支持多显示器、硬件级鼠标输入、JSON 驱动的动作编排，并提供可视化编辑器。

## 快速开始

### 安装依赖

```bash
pip install mss opencv-python numpy
```

### 运行方式

**方式一：可视化编排（推荐）**

直接双击 `editor.html` 在浏览器打开，拖拽编排动作后导出 JSON。

**方式二：命令行执行**

```bash
python main.py actions.json
```

## 项目结构

```
autoControl/
├── mouse.py           # 硬件级鼠标控制 (Win32 SendInput)
├── screen.py          # 多显示器截图 (mss)
├── template.py        # 图像模板匹配 (OpenCV)
├── engine.py          # 事件引擎 — 读取 JSON 编排并执行
├── main.py            # CLI 入口
├── editor.html        # 可视化 JSON 编排编辑器
├── actions.json       # 示例配置文件
├── templates/         # 模板图片存放目录
└── README.md
```

## 模块说明

| 模块 | 职责 |
|---|---|
| `mouse.py` | 通过 Win32 `SendInput` API 实现硬件级鼠标移动、左/右键点击 |
| `screen.py` | 基于 `mss` 的多显示器截图，支持指定显示器捕获，坐标全局转换 |
| `template.py` | OpenCV 模板匹配，支持中文路径，返回匹配位置与置信度 |
| `engine.py` | `ActionEngine` 类，读取 JSON 配置，按顺序执行动作，支持变量引用 |
| `main.py` | CLI 入口：`python main.py <config.json>` |
| `editor.html` | 可视化编排编辑器，拖拽编排、属性编辑、实时预览、JSON 导入/导出 |

## JSON 配置格式

```json
{
    "monitor": 1,
    "template_dir": "templates",
    "actions": [
        { "type": "动作类型", ... }
    ]
}
```

| 顶层字段 | 说明 |
|---|---|
| `monitor` | 默认显示器编号（1=主显示器） |
| `template_dir` | 模板图片搜索目录（相对路径） |
| `actions` | 动作列表，按顺序执行 |

## 动作类型参考

### click — 鼠标点击

```json
{
    "type": "click",
    "x": 500,
    "y": 300,
    "button": "left"
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `x` | number/string | X 坐标，支持变量引用 `{id.center_x}` |
| `y` | number/string | Y 坐标，支持变量引用 `{id.center_y}` |
| `button` | string | `"left"` 左键 / `"right"` 右键 |

### move — 鼠标移动

```json
{
    "type": "move",
    "x": 800,
    "y": 600
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `x` | number/string | X 坐标，支持变量引用 |
| `y` | number/string | Y 坐标，支持变量引用 |

### recognize — 图像识别

```json
{
    "type": "recognize",
    "id": "search_btn",
    "template": "search.jpg",
    "threshold": 0.8,
    "monitor": 1,
    "retry_interval": 1,
    "timeout": 30,
    "on_success": [
        { "type": "click", "x": "{search_btn.center_x}", "y": "{search_btn.center_y}", "button": "left" }
    ],
    "on_failure": [
        { "type": "wait", "duration": 1 }
    ]
}
```

| 字段 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `id` | string | - | 动作标识，用于变量引用 |
| `template` | string | - | 模板图片路径（相对/绝对） |
| `threshold` | number | 0.8 | 匹配阈值 0.0~1.0 |
| `monitor` | number | 1 | 目标显示器编号 |
| `retry_interval` | number | 0 | 重试间隔（秒） |
| `timeout` | number | 0 | 超时（秒），0=单次检测 |
| `on_success` | array | [] | 匹配成功时执行的动作列表 |
| `on_failure` | array | [] | 匹配失败时执行的动作列表 |

**变量引用**：设置 `id` 后，可在后续动作中使用 `{id.center_x}`、`{id.center_y}`、`{id.confidence}`、`{id.found}`。

### wait — 等待

```json
{
    "type": "wait",
    "duration": 2
}
```

| 字段 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `duration` | number | 1 | 等待秒数 |

### group — 分组

```json
{
    "type": "group",
    "actions": [
        { "type": "click", "x": 100, "y": 200, "button": "left" },
        { "type": "wait", "duration": 1 }
    ]
}
```

### loop — 循环

```json
{
    "type": "loop",
    "count": 5,
    "interval": 0.5,
    "actions": [
        { "type": "click", "x": 500, "y": 300, "button": "left" }
    ]
}
```

| 字段 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `count` | number | 1 | 循环次数 |
| `interval` | number | 0 | 每轮间隔（秒） |

## 变量引用系统

识别动作设置 `id` 后会产生以下变量：

| 变量 | 类型 | 说明 |
|---|---|---|
| `{id.found}` | bool | 是否找到 |
| `{id.center_x}` | number | 匹配位置中心 X（全局坐标） |
| `{id.center_y}` | number | 匹配位置中心 Y（全局坐标） |
| `{id.confidence}` | number | 匹配置信度 |

支持在 `click.x`、`click.y`、`move.x`、`move.y`、`recognize.template` 等字段中使用。

## 可视化编辑器

`editor.html` 提供完整的可视化编排体验：

- **拖拽添加**：从左侧面板拖入动作到时间线
- **拖拽排序**：时间线中拖拽调整顺序
- **属性编辑**：选中动作后右侧面板编辑参数
- **嵌套展开**：group/loop 展开后拖入子动作
- **图片预览**：选择模板图片后实时显示缩略图
- **变量提示**：自动检测已设置的 ID 并显示可用变量
- **JSON 导出/导入**：`Ctrl+S` 导出，支持导入已有配置修改
- **一键清空**：清空所有动作重新编排

## 事件执行日志

所有动作执行时自动打印日志（无需额外配置）：

```
[CLICK] (800, 600) 左键
[MOVE] → (100, 200)
[RECOGNIZE] 搜索模板: search.jpg
  → ✓ 找到, 坐标=(800, 600), 置信度=85.00%
[WAIT] 2秒
[GROUP] 开始执行 3 个子动作
[LOOP] 第 2/5 轮
```

## 完整示例

```json
{
    "monitor": 1,
    "template_dir": "templates",
    "actions": [
        {
            "id": "search_btn",
            "type": "recognize",
            "template": "search.jpg",
            "threshold": 0.8,
            "retry_interval": 1,
            "timeout": 30,
            "on_success": [
                {
                    "type": "click",
                    "x": "{search_btn.center_x}",
                    "y": "{search_btn.center_y}",
                    "button": "left"
                }
            ],
            "on_failure": [
                { "type": "wait", "duration": 3 }
            ]
        },
        {
            "type": "wait",
            "duration": 2
        },
        {
            "type": "group",
            "actions": [
                { "type": "click", "x": 100, "y": 200, "button": "left" },
                { "type": "wait", "duration": 1 }
            ]
        },
        {
            "type": "loop",
            "count": 3,
            "interval": 0.5,
            "actions": [
                { "type": "click", "x": 500, "y": 300, "button": "right" }
            ]
        }
    ]
}
```
