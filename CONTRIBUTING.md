# 贡献指南

感谢你对 译智通 (AI Translator) 的兴趣！我们欢迎所有形式的贡献。

## 如何贡献

### 报告 Bug

如果你发现了 bug，请在提交 Issue 前：

1. 确认该问题尚未被报告
2. 使用最新的代码版本测试
3. 提供详细的复现步骤

### 提交功能请求

如果你有新功能的想法：

1. 先搜索是否已有类似请求
2. 清晰描述功能和使用场景
3. 如果可能，提供实现思路

### 提交代码

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

#### 代码规范

- Python 代码遵循 PEP 8
- JavaScript/Vue 代码使用 ESLint 配置
- 提交信息使用中文或英文，清晰描述更改内容

## 开发环境设置

```bash
# 克隆你的 fork
git clone https://github.com/YOUR_USERNAME/joe-ai-translator.git
cd joe-ai-translator

# 安装后端依赖
cd backend
pip install -r requirements.txt

# 安装前端依赖
cd ../frontend
npm install

# 启动开发服务器
cd ..
python start.py
```

## 行为准则

- 尊重所有参与者
- 接受建设性的批评
- 关注对社区最有利的事情

## 许可证

通过贡献代码，你同意你的贡献将在 MIT 许可证下发布。