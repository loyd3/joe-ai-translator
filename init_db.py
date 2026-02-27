#!/usr/bin/env python3
"""
数据库初始化脚本 - 创建 aitranslator 数据库和表
"""

import sys
import os
import subprocess

# 添加 backend 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

def init_database():
    """初始化数据库表"""
    print("🔄 正在初始化数据库...")
    print("📊 数据库: aitranslator")
    
    try:
        from app.database import init_database as db_init
        db_init()
        
        print("✅ 数据库初始化完成！")
        print("📋 已创建表:")
        print("   • translation_history - 翻译历史记录")
        print("   • batch_translations  - 批量翻译任务")
        print("")
        print("💡 提示: 确保 MySQL 服务正在运行，且数据库 aitranslator 已创建")
        print("   创建数据库命令: CREATE DATABASE aitranslator CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        
    except Exception as e:
        print(f"\n❌ 数据库初始化失败: {e}")
        print("\n🔧 请检查:")
        print("   1. MySQL 服务是否已启动")
        print("   2. .env 文件中的数据库连接配置是否正确")
        print("   3. 数据库 'aitranslator' 是否已创建")
        sys.exit(1)

if __name__ == "__main__":
    init_database()
