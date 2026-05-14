#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""独立入口脚本 — 与 Hermes gateway run.py 的调用路径兼容。

Gateway 通过以下方式调用:
    subprocess.run([venv_python, "feishu_card_send.py", "--input", payload_path])

此文件是 feishu_card_builder.cli 的薄包装，保持向后兼容。
"""

import sys
from pathlib import Path

# 确保包可以被导入（当作为独立脚本运行时）
_script_dir = Path(__file__).resolve().parent
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))

from feishu_card_builder.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
