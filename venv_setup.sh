#!/usr/bin/env bash
# setup.sh
# 使用方法: bash setup.sh

set -e  # 遇到错误立即退出

PROJECT_DIR=$(pwd)
VENV_DIR="$PROJECT_DIR/.venv"

echo "=== Step 0: 检查系统依赖 ==="
if ! python3.12 -m venv --help >/dev/null 2>&1; then
    echo "ERROR: python3.12-venv not found. Install with:"
    echo "       sudo apt install python3.12-venv"
    exit 1
fi

echo "=== Step 1: 创建虚拟环境 ==="
rm -rf "$VENV_DIR"
python3.12 -m venv "$VENV_DIR"
echo "Virtual environment created at $VENV_DIR"

echo "=== Step 2: 激活虚拟环境 ==="
source "$VENV_DIR/bin/activate"

echo "=== Step 3: 升级 pip/setuptools/wheel ==="
python -m ensurepip --upgrade
python -m pip install --upgrade pip setuptools wheel
python -m pip --version

echo "=== Step 4: 安装开发依赖 (pytest, ruff) ==="
python -m pip install pytest ruff chardet pytest-asyncio pandas numpy
python -m pip list

echo "=== Step 5: 安装项目为 editable ==="
python -m pip install -e .
python -c "import backtesting; print('backtesting package path:', backtesting.__file__)"

echo "=== Setup complete! ==="
echo "Activate your venv with: source .venv/bin/activate"
