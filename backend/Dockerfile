FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖 (MySQL 客户端等)
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    pkg-config \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装迁移脚本依赖
RUN pip install --no-cache-dir pymysql

# 复制代码
COPY . .

# 暴露端口
EXPOSE 8000

# 复制启动脚本
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# 启动命令（先执行迁移，再启动服务）
CMD ["/app/start.sh"]
