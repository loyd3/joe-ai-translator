#!/usr/bin/env python3
"""
数据库初始化脚本
"""

import sys
import os

# 添加 backend 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app.database import engine, Base
from app.models.models import TranslationHistory, BatchTranslation

def init_database():
    """初始化数据库表"""
    print("🔄 正在初始化数据库...")
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    print("✅ 数据库初始化完成！")
    print("📊 已创建表:")
    print("   - translation_history (翻译历史)")
    print("   - batch_translations (批量翻译任务)")

if __name__ == "__main__":
    init_database()
