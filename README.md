# 🌐 译智通 (AI Translator)

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![Vue 3](https://img.shields.io/badge/vue-3-green.svg)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> 一款支持多模型 AI 的智能翻译助手，提供高质量、上下文感知的翻译服务。

---

## ✨ 功能特性

### 🤖 多模型 AI 支持
- **OpenAI** - GPT-4, GPT-3.5-turbo 等系列
- **DeepSeek** - deepseek-chat, deepseek-coder
- **SiliconFlow** - DeepSeek-V3, Qwen 等多种开源模型
- **自定义 API** - 支持任何兼容 OpenAI API 格式的端点

### 🌍 多语言翻译
- **50+ 种语言支持** - 覆盖全球主要语言
- **自动语言检测** - 智能识别源语言
- **专业领域翻译** - 技术、医学、法律等专业术语优化

### 💾 翻译历史与收藏
- **翻译历史记录** - 自动保存所有翻译记录
- **收藏夹功能** - 保存常用翻译结果
- **批量导出** - 支持 JSON、CSV 格式导出

### 🚀 批量翻译
- **文件上传** - 支持 TXT、Markdown、JSON 文件
- **批量处理** - 一次性翻译多个文本片段
- **进度追踪** - 实时显示翻译进度

---

## 🚀 快速开始

### 前置要求

1. **MySQL 数据库**（数据库名: `aitranslator`）
2. **Node.js** (v20+) 和 **Python** (v3.11+)

### 一键启动

```bash
# 克隆项目
git clone https://github.com/loyd3/joe-ai-translator.git
cd joe-ai-translator

# 配置环境变量
cp .env.example .env
# 编辑 .env，配置你的 AI API Key 和 MySQL 密码

# 初始化数据库 (方式1: 自动)
python init_db.py

# 或者使用 SQL 文件 (方式2: 需要 mysql 客户端)
python init_db.py --sql
# 或者直接执行 SQL
mysql -u root -p < init.sql

# 一键启动
python start.py
```

访问 http://localhost:5173

### Docker 部署

```bash
docker-compose up -d
```

---

## 📁 项目结构

```
joe-ai-translator/
├── start.py              # 一键启动脚本
├── init_db.py            # 数据库初始化脚本
├── init.sql              # 数据库初始化 SQL 文件
├── .env.example          # 环境变量模板
├── backend/              # FastAPI 后端
│   ├── app/
│   │   ├── api/         # API 路由
│   │   ├── core/        # AI 客户端和配置
│   │   ├── models/      # 数据库模型
│   │   └── services/    # 业务逻辑
│   └── requirements.txt
├── frontend/            # Vue3 前端
│   └── src/
│       ├── components/  # UI 组件
│       ├── views/       # 页面视图
│       └── stores/      # Pinia 状态管理
└── docs/                # 文档
```

---

## 🔧 配置说明

### MySQL 数据库配置

项目默认使用 MySQL，数据库名为 `aitranslator`。

```bash
# MySQL 配置示例（请把 password 改成你的 MySQL root 密码）
DATABASE_URL=mysql+pymysql://root:你的密码@localhost:3306/aitranslator?charset=utf8mb4

# 连接池配置
DB_POOL_SIZE=5          # 连接池大小
DB_MAX_OVERFLOW=10      # 最大溢出连接
DB_POOL_RECYCLE=3600    # 连接回收时间（秒）
```

若出现 **Access denied for user 'root'@'localhost' (using password: YES)**：
- 在项目根目录或 `backend/` 下的 `.env` 中，将 `DATABASE_URL` 里的密码改为你本机 MySQL root 的密码。
- 确认 MySQL 服务已启动，且该用户有权限访问 `aitranslator` 数据库。

#### 创建数据库

**方式1: 使用 SQL 文件 (推荐)**

```bash
# 方法 A: 使用 init_db.py 脚本
python init_db.py --sql

# 方法 B: 直接执行 SQL 文件
mysql -u root -p < init.sql
```

**方式2: 手动创建**

```bash
# 登录 MySQL
mysql -u root -p

# 创建数据库
CREATE DATABASE aitranslator CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 使用数据库并创建表
USE aitranslator;
SOURCE init.sql;
```

#### 数据库表结构

| 表名 | 说明 | 主要字段 |
|------|------|----------|
| `translation_history` | 翻译历史记录 | source_text, translated_text, source_lang, target_lang, is_favorite |
| `batch_translations` | 批量翻译任务 | items(JSON), total_items, completed_items, status |
| `system_settings` | 系统配置 | setting_key, setting_value |

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `AI_PROVIDER` | AI 提供商 | `deepseek` |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | - |
| `DATABASE_URL` | MySQL 连接字符串 | `mysql+pymysql://root:password@localhost:3306/aitranslator?charset=utf8mb4` |

---

## 📝 更新日志

### v1.0.0
- ✅ 多模型 AI 翻译支持
- ✅ 50+ 种语言互译
- ✅ 翻译历史记录
- ✅ 批量翻译功能
- ✅ 文件上传翻译

---

## 📄 许可证

[MIT License](./LICENSE)
