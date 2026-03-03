#!/bin/bash
# ============================================
# AI Translator - 一键更新并重启 Docker
#
# 功能：
#   1. 构建新的 Docker 镜像
#   2. （可选）推送到 Docker Hub
#   3. 重启本地 Docker 容器
#
# 用法:
#   ./docker-update.sh [版本号]        # 构建 + 推送 + 重启（需先 docker login）
#   ./docker-update.sh --local [版本号] # 仅本地构建 + 重启（无需登录 Docker Hub）
# 示例:
#   ./docker-update.sh 1.0.1
#   ./docker-update.sh --local
# ============================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置
DOCKER_USER="loyd3"
BACKEND_IMAGE="${DOCKER_USER}/joe-ai-translator-backend"
FRONTEND_IMAGE="${DOCKER_USER}/joe-ai-translator-frontend"
COMPOSE_FILE="docker-compose.local-db.yml"

# 解析参数：--local 表示仅本地构建，不推送
PUSH_TO_HUB=true
VERSION="latest"
for arg in "$@"; do
    if [ "$arg" = "--local" ]; then
        PUSH_TO_HUB=false
    elif [ "$arg" != "" ] && [ "$arg" != "--local" ]; then
        VERSION="$arg"
    fi
done

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  AI Translator - Docker 更新脚本${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "版本: ${YELLOW}${VERSION}${NC}"
if [ "$PUSH_TO_HUB" = false ]; then
    echo -e "模式: ${YELLOW}仅本地（不推送 Docker Hub）${NC}"
fi
echo ""

# 检查 Docker 是否运行
echo -e "${BLUE}▶ 检查 Docker...${NC}"
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}✗ Docker 未运行${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker 已就绪${NC}"

# 仅在需要推送时检查 Docker Hub 登录
if [ "$PUSH_TO_HUB" = true ]; then
    echo -e "${BLUE}▶ 检查 Docker Hub 登录状态...${NC}"
    if ! docker info 2>/dev/null | grep -q "Username"; then
        echo -e "${RED}✗ 未登录到 Docker Hub${NC}"
        echo "请先运行: docker login"
        echo "或仅本地构建: ./docker-update.sh --local"
        exit 1
    fi
    echo -e "${GREEN}✓ Docker Hub 已登录${NC}"
fi
echo ""

# 停止现有容器
echo -e "${BLUE}▶ 停止现有容器...${NC}"
docker-compose -f ${COMPOSE_FILE} down
echo -e "${GREEN}✓ 容器已停止${NC}"
echo ""

# 构建新镜像
echo -e "${BLUE}▶ 构建后端镜像...${NC}"
docker build -t ${BACKEND_IMAGE}:${VERSION} -t ${BACKEND_IMAGE}:latest ./backend

echo ""
echo -e "${BLUE}▶ 构建前端镜像...${NC}"
docker build -t ${FRONTEND_IMAGE}:${VERSION} -t ${FRONTEND_IMAGE}:latest ./frontend

echo ""
echo -e "${GREEN}✓ 镜像构建完成${NC}"
echo ""

# 按需推送到 Docker Hub
if [ "$PUSH_TO_HUB" = true ]; then
    echo -e "${BLUE}▶ 推送后端镜像到 Docker Hub...${NC}"
    docker push ${BACKEND_IMAGE}:${VERSION}
    docker push ${BACKEND_IMAGE}:latest
    echo ""
    echo -e "${BLUE}▶ 推送前端镜像到 Docker Hub...${NC}"
    docker push ${FRONTEND_IMAGE}:${VERSION}
    docker push ${FRONTEND_IMAGE}:latest
    echo ""
    echo -e "${GREEN}✓ 镜像推送完成${NC}"
    echo ""
fi

# 启动新容器
echo -e "${BLUE}▶ 启动新容器...${NC}"
docker-compose -f ${COMPOSE_FILE} up -d

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ✓ 更新完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "镜像地址:"
echo -e "  ${YELLOW}${BACKEND_IMAGE}:${VERSION}${NC}"
echo -e "  ${YELLOW}${FRONTEND_IMAGE}:${VERSION}${NC}"
echo ""
echo -e "本地访问地址:"
echo -e "  🌐 前端: ${BLUE}http://localhost:8081${NC}"
echo -e "  🔌 后端: ${BLUE}http://localhost:8002${NC}"
echo ""
echo -e "查看日志:"
echo -e "  ${BLUE}docker logs -f ai-translator-backend${NC}"
echo -e "  ${BLUE}docker logs -f ai-translator-frontend${NC}"
echo ""
