#!/usr/bin/env bash
set -e

# 1. Kích hoạt virtualenv
#    Giả sử venv của bạn ở ../venv310 so với thư mục scripts
source "$(dirname "$0")"/../venv310/Scripts/activate

# 2. Cài pytest nếu chưa có (tuỳ chọn, hoặc bạn đã để trong requirements.txt)
pip install pydantic-settings
pip install -r "$(dirname "$0")"/../requirements.txt



echo "Running tests..."
pytest --maxfail=1 --disable-warnings -q
