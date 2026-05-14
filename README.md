# hermes-feishu-cardmsg

飞书/Lark 交互式卡片消息构建器。从 Markdown 文本自动生成飞书 Schema 2.0 交互式卡片 JSON。

## 组成部分

本项目包含三个组件，配合使用：

1. **`feishu_card_builder/`** — Python 包，负责将 Markdown 转为飞书卡片 JSON
2. **`feishu_card_send.py`** — 独立入口脚本，gateway 通过 subprocess 调用
3. **`patches/`** — 对 hermes-agent `gateway/run.py` 的 patch（`local/feishu-card-footer` 分支）

## 架构

```
Hermes gateway (run.py, local/feishu-card-footer 分支)
  └─ subprocess ─→ ~/.hermes/scripts/feishu_card_send.py
                      └─→ feishu_card_builder (venv 中)
                             ├─ 解析 AI 回复（reasoning/tools/footer）
                             ├─ 构建 Schema 2.0 卡片 JSON
                             └─ lark-cli im +messages-send
```

## hermes update 后重新应用

```bash
# 方式一：使用脚本
./scripts/apply-patch.sh

# 方式二：手动
cd ~/.hermes/hermes-agent
git checkout local/feishu-card-footer
git rebase main
# 如有冲突，解决后 git rebase --continue

# 确保 feishu_card_builder 已安装
~/.hermes/hermes-agent/venv/bin/pip install git+https://github.com/ztp559/hermes-feishu-cardmsg.git
```

## 安装（首次）

```bash
# 1. 安装 Python 包到 venv
~/.hermes/hermes-agent/venv/bin/pip install git+https://github.com/ztp559/hermes-feishu-cardmsg.git

# 2. 放置入口脚本
cp feishu_card_send.py ~/.hermes/scripts/feishu_card_send.py

# 3. 应用 gateway patch
cd ~/.hermes/hermes-agent
git checkout -b local/feishu-card-footer main
git am patches/0001-feat-gateway-feishu-card-message.patch
```

## 快速开始

```python
from feishu_card_builder import CardBuilder

# 自动模式：传入完整 AI 回复
card_json = CardBuilder().build("""
[[HERMES_STATUS:completed]]

## 分析结果

主体内容...

[[HERMES_REASONING]]
思考过程...
[[/HERMES_REASONING]]

[[HERMES_FOOTER]]
已完成 · 耗时 2.5s · gpt-4
[[/HERMES_FOOTER]]
""")

# 手动模式：链式构建
from feishu_card_builder import StatusType

card_json = (
    CardBuilder()
    .set_title("标题")
    .set_status(StatusType.COMPLETED)
    .add_body("内容")
    .add_thinking("思考...")
    .set_footer("耗时 1s")
    .build_from_parts()
)
```

## 标记格式

| 标记 | 用途 |
|------|------|
| `[[HERMES_STATUS:thinking\|completed\|ended]]` | 状态标记 |
| `[[HERMES_REASONING]]...[[/HERMES_REASONING]]` | 思考过程 |
| `<think>...</think>` | 思考过程（兼容格式） |
| `[[HERMES_TOOLS]]...[[/HERMES_TOOLS]]` | 工具调用 |
| `[[HERMES_FOOTER]]...[[/HERMES_FOOTER]]` | Footer 内容 |

## 飞书 Schema 2.0 限制

- Markdown 不支持 heading 标签（用 emoji+bold 模拟层级）
- 不支持 `<u>` 下划线（自动去除）
- 图片需上传到飞书获取 img_key
- Footer 中的 `<text_tag>` 需要用 `div` + `lark_md` 而非纯 `markdown` 元素

## License

MIT
