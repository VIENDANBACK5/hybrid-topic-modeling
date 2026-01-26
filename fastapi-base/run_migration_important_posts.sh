#!/bin/bash
# Script để chạy migration cho bảng important_posts

cd /home/ai_team/lab/pipeline_mxh/fastapi-base

# Kích hoạt virtual environment
source .venv/bin/activate

# Chạy migration
alembic upgrade head

echo "✅ Migration hoàn tất! Bảng important_posts đã được tạo."
