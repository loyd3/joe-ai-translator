#!/usr/bin/env python3
"""
数据库初始化脚本 - 支持两种方式:
1. 自动方式: 使用 SQLAlchemy ORM 自动创建表
2. SQL文件方式: 执行 init.sql 脚本
"""

import sys
import os
import subprocess
import argparse

# 添加 backend 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

def init_by_sql():
    """使用 SQL 文件初始化数据库"""
    print("🔄 使用 SQL 文件初始化数据库...")
    print("📊 数据库: aitranslator")
    
    sql_file = os.path.join(os.path.dirname(__file__), "init.sql")
    
    if not os.path.exists(sql_file):
        print(f"❌ 找不到 SQL 文件: {sql_file}")
        return False
    
    try:
        # 读取 SQL 文件内容
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 执行 SQL
        result = subprocess.run(
            ['mysql', '-u', 'root', '-p'],
            input=sql_content,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        
        if result.returncode == 0:
            print("✅ SQL 文件执行成功！")
            print("📋 已创建表:")
            print("   • translation_history - 翻译历史记录")
            print("   • batch_translations  - 批量翻译任务")
            print("   • system_settings     - 系统配置")
            return True
        else:
            print(f"❌ SQL 执行失败:")
            print(result.stderr)
            return False
            
    except FileNotFoundError:
        print("❌ 未找到 mysql 命令，请确保 MySQL 客户端已安装")
        print("💡 尝试使用自动方式...")
        return init_auto()
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def init_auto():
    """使用 SQLAlchemy ORM 自动创建表"""
    print("🔄 使用 ORM 自动初始化数据库...")
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
        return True
        
    except Exception as e:
        print(f"\n❌ 数据库初始化失败: {e}")
        print("\n🔧 请检查:")
        print("   1. MySQL 服务是否已启动")
        print("   2. .env 文件中的数据库连接配置是否正确")
        print("   3. 数据库 'aitranslator' 是否已创建")
        return False

def main():
    parser = argparse.ArgumentParser(description='初始化 AI Translator 数据库')
    parser.add_argument('--sql', action='store_true', help='使用 SQL 文件方式初始化 (需要 mysql 客户端)')
    parser.add_argument('--auto', action='store_true', help='使用 ORM 自动方式初始化 (默认)')
    args = parser.parse_args()
    
    print("=" * 60)
    print("  🌐 AI Translator 数据库初始化工具")
    print("=" * 60)
    print()
    
    success = False
    
    if args.sql:
        success = init_by_sql()
    else:
        # 默认使用自动方式
        success = init_auto()
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
