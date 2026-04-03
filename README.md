# 🌐 译智通 (AI Translator)

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![Vue 3](https://img.shields.io/badge/vue-3-green.svg)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](./docker-compose.yml)

> 一款支持多模型 AI 的智能翻译助手，提供高质量、上下文感知的翻译服务。
> 
> **✨ 特色：文学翻译功能** - 采用 AI 四步翻译流程，追求音美、词美、意美的文学翻译品质。

[English README](./README_EN.md) | [在线演示](https://your-demo-url.com) | [文档](https://your-docs-url.com)

---

## 📸 界面预览

| 普通翻译 | 文学翻译 |
|---------|---------|
| ![普通翻译](./docs/images/normal-translate.png) | ![文学翻译](./docs/images/literary-translate.png) |

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

### 📚 文学翻译
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

### 方式一：Docker 部署（推荐）

```bash
# 克隆项目
git clone https://github.com/loyd3/joe-ai-translator.git
cd joe-ai-translator

# 配置环境变量
cp .env.example .env
# 编辑 .env，配置你的 AI API Key

# 启动服务
docker-compose up -d

# 访问 http://localhost:5173
```

### 方式二：本地开发

#### 前置要求

- **Node.js** v20+
- **Python** v3.11+
- **MySQL** 8.0+

#### 安装步骤

```bash
# 克隆项目
git clone https://github.com/loyd3/joe-ai-translator.git
cd joe-ai-translator

# 配置环境变量
cp .env.example .env
# 编辑 .env，配置你的 AI API Key 和 MySQL 连接信息

# 初始化数据库
python init_db.py

# 一键启动前后端
python start.py
```

访问 http://localhost:5173

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
├── docker-compose.yml    # Docker 部署配置
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
│       ├── router/      # 路由配置
│       └── api/         # API 客户端
└── docs/                # 文档
```

---

## 🔧 配置说明

### 环境变量

| 变量 | 说明 | 必填 | 默认值 |
|------|------|------|--------|
| `AI_PROVIDER` | AI 提供商 | 否 | `deepseek` |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | 是* | - |
| `OPENAI_API_KEY` | OpenAI API Key | 是* | - |
| `SILICONFLOW_API_KEY` | SiliconFlow API Key | 是* | - |
| `DATABASE_URL` | MySQL 连接字符串 | 否 | `mysql+pymysql://root:password@localhost:3306/aitranslator?charset=utf8mb4` |

> *至少配置一个 AI 提供商的 API Key

### MySQL 数据库配置

```bash
# MySQL 配置示例
DATABASE_URL=mysql+pymysql://root:你的密码@localhost:3306/aitranslator?charset=utf8mb4
```

#### 创建数据库

```bash
# 使用 init_db.py 脚本
python init_db.py

# 或者手动执行 SQL
mysql -u root -p < init.sql
```

---

## 🤝 贡献指南

我们欢迎所有形式的贡献！

1. **Fork** 本仓库
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的修改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 **Pull Request**

详见 [CONTRIBUTING.md](./CONTRIBUTING.md)

---

## 📝 更新日志

详见 [CHANGELOG.md](./CHANGELOG.md)

### 最近更新

**v1.1.0** (2025-02-28)
- ✅ 文学翻译功能 - AI 四步翻译流程
- ✅ 三美原则评估 - 音美、词美、意美
- ✅ RAG 参考文档支持
- ✅ 段落对照编辑

---

## 🛣️ 路线图

- [ ] 支持更多 AI 模型（Claude、Gemini 等）
- [ ] 实时协作翻译
- [ ] 翻译记忆库（TM）
- [ ] 插件系统
- [ ] 移动端 App

---

## 📄 许可证

本项目采用 [MIT License](./LICENSE) 开源许可证。

---

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 高性能 Python Web 框架
- [Vue.js](https://vuejs.org/) - 渐进式 JavaScript 框架
- [DeepSeek](https://deepseek.com/) - 优秀的国产大模型
- [SiliconFlow](https://siliconflow.cn/) - 开源模型 API 平台

---

## 📮 联系我们

- 提交 Issue: [GitHub Issues](https://github.com/loyd3/joe-ai-translator/issues)
- 邮箱: your-email@example.com

---

<p align="center">
  如果这个项目对你有帮助，请给我们一个 ⭐️ Star！
</p>
