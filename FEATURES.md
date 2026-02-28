# 文学翻译功能说明

## 功能概述

本次为 joe-ai-translator 添加了完整的文学翻译功能，实现了用户要求的所有功能点。

## 已实现功能

### 1. 全文翻译 ✓
- 支持导入长文本进行自动翻译
- 支持多种文件格式（txt, md 等）
- 文本自动分段处理

### 2. 四步翻译流程 ✓
| 步骤 | 名称 | 功能 |
|------|------|------|
| 第1步 | 翻译 | AI 进行初译，侧重文学性表达 |
| 第2步 | 校验 | 检查准确性，评估三美原则 |
| 第3步 | 修改 | 针对性润色，提升翻译品质 |
| 第4步 | 定稿 | 最终审校，确保出版水准 |

### 3. 三美原则（文学翻译核心）✓
- **音美** - 韵律、节奏、音乐性评分
- **词美** - 用词精准度、优雅度评分
- **意美** - 意境传达、神韵保留评分

### 4. RAG 功能 ✓
- 支持上传参考文档
- 支持多种文档类型：术语库、风格指南、参考译文
- 翻译时自动将参考内容注入 AI 提示词
- 参考文档管理界面

### 5. 对照查看和修改 ✓
- 左右对照模式：原文 vs 译文
- 段落对照模式：逐段对照编辑
- 支持用户直接修改译文
- 显示编辑状态标记
- 支持导出最终译文（txt/md 格式）

## 新增文件列表

### 后端
```
backend/app/models/models.py              # 更新：新增文学翻译模型
backend/app/schemas/schemas.py            # 更新：新增文学翻译 schemas
backend/app/core/ai_client.py             # 更新：新增文学翻译方法
backend/app/api/literary_translation.py   # 新增：文学翻译 API 路由
backend/app/main.py                       # 更新：注册新路由
```

### 前端
```
frontend/src/api/index.ts                 # 更新：新增文学翻译 API
frontend/src/views/LiteraryTranslationView.vue    # 新增：文学翻译主视图
frontend/src/components/ReferenceDocManager.vue   # 新增：参考文档管理组件
frontend/src/router/index.ts              # 更新：添加新路由
frontend/src/shims-vue.d.ts               # 新增：TypeScript 类型声明
```

### 数据库
```
init.sql                                  # 更新：新增三个表
```

### 文档
```
README.md                                 # 更新：添加新功能说明
FEATURES.md                               # 新增：本功能说明文档
```

## 数据库表结构

### literary_translations（文学翻译任务表）
- 基本信息：id, title, source_text
- 四步结果：step1_translation ~ step4_finalization
- 状态：current_step, status
- 三美评分：beauty_sound_score, beauty_word_score, beauty_meaning_score
- RAG：reference_document_ids

### literary_paragraphs（段落表）
- 段落级存储，支持对照编辑
- 保存每段的四步翻译结果
- 支持用户编辑：user_edited_text, is_edited

### reference_documents（参考文档表）
- 支持术语库、风格指南等类型
- 支持语言对关联
- 可启用/禁用

## 使用方法

1. **启动应用**
   ```bash
   python start.py
   ```

2. **访问文学翻译**
   - 打开 http://localhost:5173
   - 点击侧边栏"文学翻译"

3. **创建翻译任务**
   - 选择文学类型（诗歌/散文/小说/戏剧）
   - 选择源语言和目标语言
   - 可选：添加参考文档
   - 粘贴原文
   - 点击"创建翻译任务"

4. **执行四步翻译**
   - 点击"开始翻译"执行第1步
   - 点击"执行校验"执行第2步
   - 点击"执行修改"执行第3步
   - 点击"执行定稿"执行第4步

5. **编辑和导出**
   - 在段落对照模式下直接编辑译文
   - 完成后点击"导出译文"

## API 端点

### 参考文档管理
- `POST /api/literary/references` - 创建参考文档
- `GET /api/literary/references` - 获取参考文档列表
- `GET /api/literary/references/{id}` - 获取参考文档详情
- `PUT /api/literary/references/{id}` - 更新参考文档
- `DELETE /api/literary/references/{id}` - 删除参考文档
- `POST /api/literary/references/upload` - 上传参考文档文件

### 文学翻译任务
- `POST /api/literary/translations` - 创建翻译任务
- `GET /api/literary/translations` - 获取任务列表
- `GET /api/literary/translations/{id}` - 获取任务详情
- `PUT /api/literary/translations/{id}` - 更新任务
- `DELETE /api/literary/translations/{id}` - 删除任务

### 四步翻译流程
- `POST /api/literary/translations/{id}/workflow/start` - 开始翻译
- `POST /api/literary/translations/{id}/workflow/verify` - 执行校验
- `POST /api/literary/translations/{id}/workflow/revise` - 执行修改
- `POST /api/literary/translations/{id}/workflow/finalize` - 执行定稿
- `GET /api/literary/translations/{id}/workflow` - 获取工作流状态

### 段落管理
- `GET /api/literary/translations/{id}/paragraphs` - 获取所有段落
- `PUT /api/literary/paragraphs/{id}` - 更新段落（用户编辑）

### 导出
- `POST /api/literary/translations/{id}/export` - 导出翻译结果
