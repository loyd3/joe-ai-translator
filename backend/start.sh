#!/bin/bash
# 启动脚本：先执行数据库迁移，再启动后端服务

echo "🚀 启动后端服务..."

# 执行数据库迁移
echo "📦 执行数据库迁移..."
python run_migrations.py

# 检查迁移结果
if [ $? -eq 0 ]; then
    echo "✅ 迁移完成，启动服务..."
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000
else
    echo "❌ 迁移失败，退出"
    exit 1
fi
