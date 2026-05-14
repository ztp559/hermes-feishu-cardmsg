# hermes-feishu-cardmsg

飞书/Lark 交互式卡片消息构建器。从 Markdown 文本自动生成飞书 Schema 2.0 交互式卡片 JSON。

## 安装

```bash
pip install git+https://github.com/ztp559/hermes-feishu-cardmsg.git
```

## 快速开始

```python
from feishu_card_builder import ncard_json = builder.build(content)
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
    .set_footer("已完成 · 耗时 2.5s")
    .build_from_parts()
)
```

### CLI 用法

```bash
feishu-card-send --input payload.jsR]]...[[/HERMES_FOOTER]]` | Footer 内容 |

## License

MIT
