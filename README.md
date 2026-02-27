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

1. **MySQL 数据库**（或 SQLite 用于测试）
2. **Node.js** (v20+) 和 **Python** (v3.11+)

### 一键启动

```bash
# 克隆项目
git clone https://github.com/loyd3/joe-ai-translator.git
cd joe-ai-translator

# 配置环境变量
cp .env.example .env
# 编辑 .env，配置你的 AI API Key

# 初始化数据库
python init_db.py

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

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `AI_PROVIDER` | AI 提供商 | `deepseek` |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | - |
| `DATABASE_URL` | 数据库连接 | SQLite |

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
