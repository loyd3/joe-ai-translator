# 🌐 译智通 (AI Translator)

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![Vue 3](https://img.shields.io/badge/vue-3-green.svg)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> 一款支持多模型 AI 的智能翻译助手，提供高质量、上下文感知的翻译服务。
> 
> **✨ 新增：文学翻译功能** - 采用 AI 四步翻译流程，追求音美、词美、意美的文学翻译品质。

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

### 📚 文学翻译（新增）
- **四步翻译流程** - 翻译 → 校验 → 修改 → 定稿
- **三美原则** - 音美、词美、意美的全面追求
- **多种文学体裁** - 支持诗歌、散文、小说、戏剧
- **RAG 参考文档** - 可上传术语库、风格指南作为翻译参考
- **对照编辑** - 原文译文段落级对照，支持人工精修

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

## 📚 文学翻译使用指南

### 四步翻译流程

1. **翻译** - AI 进行初译，注重忠实原文的同时兼顾文学性
2. **校验** - AI 对照原文检查准确性，并评估三美原则（音美、词美、意美）
3. **修改** - 根据校验反馈进行针对性润色和提升
4. **定稿** - 最终审校，确保达到出版品质

### RAG 参考文档

在创建翻译任务时，可以选择参考文档：
- **术语库** - 确保专业术语翻译一致
- **风格指南** - 保持特定风格或作者的翻译风格
- **参考译文** - 参考已有译文保持风格统一

### 三美原则说明

- **音美** - 译文的韵律、节奏、音乐性
- **词美** - 用词的精准度、优雅度、质感
- **意美** - 意境的传达、神韵的保留

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
│   │   │   ├── translate.py           # 普通翻译 API
│   │   │   └── literary_translation.py # 文学翻译 API（新增）
│   │   ├── core/        # AI 客户端和配置
│   │   │   └── ai_client.py           # AI 客户端（含文学翻译方法）
│   │   ├── models/      # 数据库模型
│   │   │   └── models.py              # 数据模型（新增文学翻译表）
│   │   └── services/    # 业务逻辑
│   └── requirements.txt
├── frontend/            # Vue3 前端
│   └── src/
│       ├── components/  # UI 组件
│       │   └── ReferenceDocManager.vue # 参考文档管理（新增）
│       ├── views/       # 页面视图
│       │   ├── TranslatorView.vue      # 普通翻译
│       │   └── LiteraryTranslationView.vue # 文学翻译（新增）
│       ├── router/      # 路由配置
│       └── api/         # API 客户端
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
| `literary_translations` | 文学翻译任务（新增） | 四步翻译结果、三美评分、RAG参考 |
| `literary_paragraphs` | 文学翻译段落（新增） | 段落级对照、用户编辑 |
| `reference_documents` | RAG参考文档（新增） | 术语库、风格指南 |
| `system_settings` | 系统配置 | setting_key, setting_value |

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `AI_PROVIDER` | AI 提供商 | `deepseek` |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | - |
| `DATABASE_URL` | MySQL 连接字符串 | `mysql+pymysql://root:password@localhost:3306/aitranslator?charset=utf8mb4` |

---

## 📝 更新日志

### v1.1.0 (2025-02-28)
- ✅ **文学翻译功能** - AI 四步翻译流程
- ✅ **三美原则** - 音美、词美、意美评估
- ✅ **RAG 参考文档** - 支持术语库、风格指南
- ✅ **段落对照编辑** - 原文译文对照查看和修改
- ✅ **多种文学体裁** - 诗歌、散文、小说、戏剧

### v1.0.0
- ✅ 多模型 AI 翻译支持
- ✅ 50+ 种语言互译
- ✅ 翻译历史记录
- ✅ 批量翻译功能
- ✅ 文件上传翻译

---

## 📄 许可证

[MIT License](./LICENSE)
