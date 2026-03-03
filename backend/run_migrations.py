#!/usr/bin/env python3
"""
数据库迁移脚本
自动执行 migrations/ 目录下的所有 .sql 文件
按文件名排序执行，确保顺序正确
"""
import os
import sys
import glob
import pymysql
from datetime import datetime

# 数据库配置（从环境变量读取，兼容 Docker）
DB_HOST = os.getenv('MYSQL_HOST', 'mysql')
DB_PORT = int(os.getenv('MYSQL_PORT', '3306'))
DB_USER = os.getenv('MYSQL_USER', 'root')
DB_PASSWORD = os.getenv('MYSQL_PASSWORD', 'rootpassword')
DB_NAME = os.getenv('MYSQL_DATABASE', 'aitranslator')

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), 'migrations')
MIGRATIONS_TABLE = '_migrations'  # 记录已执行的迁移

def get_connection():
    """获取数据库连接"""
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset='utf8mb4',
        autocommit=False
    )

def init_migrations_table(cursor):
    """创建迁移记录表"""
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} (
            id INT AUTO_INCREMENT PRIMARY KEY,
            filename VARCHAR(255) NOT NULL UNIQUE,
            executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

def get_executed_migrations(cursor):
    """获取已执行的迁移文件列表"""
    try:
        cursor.execute(f"SELECT filename FROM {MIGRATIONS_TABLE}")
        return {row[0] for row in cursor.fetchall()}
    except:
        return set()

def record_migration(cursor, filename):
    """记录迁移已执行"""
    cursor.execute(f"INSERT INTO {MIGRATIONS_TABLE} (filename) VALUES (%s)", (filename,))

def execute_sql_file(cursor, filepath):
    """执行 SQL 文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # 分割多条语句执行
    statements = sql_content.split(';')
    for stmt in statements:
        stmt = stmt.strip()
        if stmt and not stmt.startswith('--') and not stmt.startswith('/*'):
            try:
                cursor.execute(stmt)
            except Exception as e:
                # 忽略 "已存在" 类型的错误
                error_msg = str(e).lower()
                if 'duplicate' in error_msg or 'already exists' in error_msg or 'unknown column' in error_msg:
                    print(f"  ⚠️  警告（可忽略）: {e}")
                else:
                    raise

def run_migrations():
    """运行所有待执行的迁移"""
    print(f"🔄 数据库迁移开始... [{datetime.now()}]")
    print(f"📁 Migrations 目录: {MIGRATIONS_DIR}")
    
    # 获取所有 .sql 文件并按名排序
    sql_files = sorted(glob.glob(os.path.join(MIGRATIONS_DIR, '*.sql')))
    
    if not sql_files:
        print("ℹ️  没有待执行的迁移文件")
        return
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 初始化迁移表
            init_migrations_table(cursor)
            conn.commit()
            
            # 获取已执行的迁移
            executed = get_executed_migrations(cursor)
            
            # 执行未执行的迁移
            executed_count = 0
            for filepath in sql_files:
                filename = os.path.basename(filepath)
                
                if filename in executed:
                    print(f"  ✅ 已执行过: {filename}")
                    continue
                
                print(f"  📝 执行: {filename}")
                try:
                    execute_sql_file(cursor, filepath)
                    record_migration(cursor, filename)
                    conn.commit()
                    executed_count += 1
                    print(f"     ✓ 成功")
                except Exception as e:
                    conn.rollback()
                    print(f"     ✗ 失败: {e}")
                    raise
            
            print(f"\n✅ 迁移完成: 执行了 {executed_count} 个新迁移，跳过 {len(executed)} 个已执行的")
            
    finally:
        conn.close()

if __name__ == '__main__':
    # 等待 MySQL 就绪
    max_retries = 30
    for i in range(max_retries):
        try:
            conn = get_connection()
            conn.close()
            break
        except Exception as e:
            print(f"⏳ 等待 MySQL 就绪... ({i+1}/{max_retries})")
            import time
            time.sleep(2)
    else:
        print("❌ MySQL 连接超时")
        sys.exit(1)
    
    run_migrations()
