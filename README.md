# hermes-feishu-cardmsg

飞书/Lark 交互式卡片消息构建器。从 Markdown 文本自动生成飞书 Schema 2.0 交互式卡片 JSON。

## 功能

- 自动提取思考过程（`<think>`/`[[HERMES_REASONING]]`）并显示为可折叠面板
- 自动提取工具调用并显示为可折叠面板
- Markdown 表格转飞书原生表格
- 支持标题、分割线、普通文本
- 支持状态标记（thinking/completed/ended）
- 支持自定义 Footer（耗时、token 统计、上下文进度条）
- 链式 API，灵活构建
- CLI 工具，可直接从 gateway 调用

## 架构

```
run.py (Hermes gateway)
  └─ subprocess ─→ feishu_card_send.py (薄包装)
                      └─→ feishu_card_builder.cli.main()
                             ├─ 构建 footer（模型、耗时、上下文）
                             ├─ CardBuilder().build(content)
                             └─ lark-cli im +messages-send
```

## 安装

```bash
pip install git+https://github.com/ztp559/hermes-feishu-cardmsg.git
```

## 快速开始

```python
from feishu_card_builder import CardBuilder

builder = CardBuilder()
card_json = builder.build("## 标题\n\n内容...")
```

### 自动模式

传入完整 AI 回复文本，自动解析所有部分：

```python
content = """
[[HERMES_STATUS:completed]]

## 分析结果

这是主体内容...

[[HERMES_REASONING]]
让我分析一下这个问题...
[[/HERMES_REASONING]]

[[HERMES_TOOLS]]
调用了 web_search("飞书卡片")
[[/HERMES_TOOLS]]

[[HERMES_FOOTER]]
已完成 · 耗时 2.5s · gpt-4
[[/HERMES_FOOTER]]
"""

card_json = builder.build(content)
```

### 手动模式

```python
from feishu_card_builder import CardBuilder, StatusType

card_json = (
    CardBuilder()
    .set_title("自定义标题")
    .set_status(StatusType.COMPLETED)
    .add_body("主体内容")
    .add_thinking("思考过程...")
    .add_tools("工具调用...")
    .set_footer("已完成 · 耗时 2.5s")
    .build_from_parts()
)
```

### CLI 使用

```bash
# 通过 pip install 后
feishu-card-send --input payload.json

# 或直接调用
python feishu_card_send.py --input payload.json
```

## Gateway 集成

详见 [docs/gateway_integration.md](docs/gateway_integration.md)

## 标记格式

| 标记 | 用途 |
|------|------|
| `[[HERMES_STATUS:thinking\|completed\|ended]]` | 状态标记 |
| `[[HERMES_REASONING]]...[[/HERMES_REASONING]]` | 思考过程 |
| `<think>...</think>式） |
| `[[HERMES_TOOLS]]...[[/HERMES_TOOLS]]` | 工具调用 |
| `[[HERMES_FOOTER]]...[[/HERMES_FOOTER]]` | Footer 内容 |

## 飞书 Schema 2.0 限制

- Markdown 不支持 heading 标签（用 emoji+bold 模拟层级）
- 不支持 `<u>` 下划线（自动去除）
- 图片需上传到飞书获取 img_key
- Footer 中的 `<text_tag>` 需要用 `div` + `lark_md` 而非纯 `markdown` 元素

## License

MIT
