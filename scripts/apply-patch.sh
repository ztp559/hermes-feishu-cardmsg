#!/bin/bash
# 在 hermes update 后重新应用 feishu-card-message patch
#
# 用法:
#   ./scripts/apply-patch.sh
#
# 前提:
#   - 当前在 ~/.hermes/hermes-agent 目录
#   - main 分支已更新到最新
#
# 该脚本会:
#   1. 确保 local/feishu-card-footer 分支存在
#   2. 将 patch rebase 到最新 main 上
#   3. 安装 feishu_card_builder 到 venv
#   4. 确保 feishu_card_send.py 在 ~/.hermes/scripts/ 中

set -euo pipefail

HERMES_HOME="${HOME}/.hermes"
HERMES_AGENT="${HERMES_HOME}/hermes-agent"
VENV_PIP="${HERMES_AGENT}/venv/bin/pip"
SCRIPTS_DIR="${HERMES_HOME}/scripts"
REPO_URL="https://github.com/ztp559/hermes-feishu-cardmsg.git"

cd "${HERMES_AGENT}"

echo "=== Step 1: Rebase local/feishu-card-footer onto main ==="

if git branch --list "local/feishu-card-footer" | grep -q "local/feishu-card-footer"; then
    git checkout local/feishu-card-footer
    git rebase main
    echo "✓ Branch rebased successfully"
else
    echo "Branch not found, creating from patch..."
    git checkout main
    git checkout -b local/feishu-card-footer
    PATCH_DIR="$(cd "$(dirname "$0")/../patches" && pwd)"
    if [ -f "${PATCH_DIR}/0001-feat-gateway-feishu-card-message.patch" ]; then
        git am "${PATCH_DIR}/0001-feat-gateway-feishu-card-message.patch"
        echo "✓ Branch created from patch"
    else
        echo "✗ Patch file not found at ${PATCH_DIR}"
        exit 1
    fi
fi

echo ""
echo "=== Step 2: Install feishu_card_builder into venv ==="

"${VENV_PIP}" install --quiet --upgrade "git+${REPO_URL}" 2>/dev/null \
    || "${VENV_PIP}" install --quiet --upgrade "git+${REPO_URL}"
echo "✓ feishu_card_builder installed"

echo ""
echo "=== Step 3: Ensure feishu_card_send.py exists ==="

mkdir -p "${SCRIPTS_DIR}"
if [ ! -f "${SCRIPTS_DIR}/feishu_card_send.py" ]; then
    # 从仓库中提取 cli.py 作为独立脚本
    "${HERMES_AGENT}/venv/bin/python"
from pathlib import Path
import feishu_card_builder
pkg_dir = Path(feishu_card_builder.__file__).parent
cli_src = pkg_dir / 'cli.py'
if cli_src.exists():
    print(cli_src.read_text())
" > "${SCRIPTS_DIR}/feishu_card_send.py"
    echo "✓ feishu_card_send.py created"
else
    echo "✓ feishu_card_send.py already exists"
fi

echo ""
echo "=== Done ==="
echo "Current branch: $(git branch --show-current)"
echo "Patch commit: $(git log --oneline -1)"
