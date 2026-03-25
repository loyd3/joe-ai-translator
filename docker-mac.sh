#!/usr/bin/env bash
# =============================================================================
# AI Translator — macOS 本地 Docker 一键部署
#
# 适用：Apple Silicon / Intel Mac + Docker Desktop（或 Colima 等兼容 Docker CLI 的环境）
#
# 用法（在项目根目录执行）:
#   chmod +x docker-mac.sh
#   ./docker-mac.sh              # 启动（默认）
#   ./docker-mac.sh start        # 同上
#   ./docker-mac.sh stop         # 停止并移除容器（保留数据卷）
#   ./docker-mac.sh restart      # 重启
#   ./docker-mac.sh logs         # 跟踪全部服务日志
#   ./docker-mac.sh logs backend # 只看后端
#   ./docker-mac.sh rebuild      # 无缓存重建镜像并启动
#   ./docker-mac.sh ps           # 查看状态
#   ./docker-mac.sh down-v       # 停止并删除卷（清空 MySQL 数据，慎用）
#
# 环境变量:
#   COMPOSE_FILE=docker-compose.local-db.yml ./docker-mac.sh start
#   使用自带 MySQL + translator 用户的 compose（需 .env 与 compose 中密码一致）
#
# 访问地址（默认 docker-compose.yml）:
#   前端 http://localhost:8081
#   后端 http://localhost:8002  （API 文档 http://localhost:8002/docs）
#   MySQL 宿主机端口 3308
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 项目根目录 = 本脚本所在目录
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"

# 优先使用 Docker Desktop 自带的 compose 插件
if docker compose version &>/dev/null; then
  DC=(docker compose -f "$COMPOSE_FILE")
elif command -v docker-compose &>/dev/null; then
  DC=(docker-compose -f "$COMPOSE_FILE")
else
  echo -e "${RED}未找到 docker compose 或 docker-compose，请先安装 Docker Desktop for Mac。${NC}"
  exit 1
fi

die() { echo -e "${RED}$*${NC}" >&2; exit 1; }
info() { echo -e "${BLUE}$*${NC}"; }
ok() { echo -e "${GREEN}$*${NC}"; }

check_mac() {
  if [[ "$(uname -s)" != "Darwin" ]]; then
    echo -e "${YELLOW}提示: 当前不是 macOS，脚本仍可使用（路径与命令通用）。${NC}"
  fi
}

check_docker() {
  if ! docker info &>/dev/null; then
    die "Docker 未运行。请在 Mac 上打开 Docker Desktop，或启动 Colima: colima start"
  fi
}

ensure_env() {
  if [[ ! -f .env ]]; then
    if [[ -f .env.example ]]; then
      info "未找到 .env，从 .env.example 复制..."
      cp .env.example .env
      ok "已创建 .env，请编辑后填入 DEEPSEEK_API_KEY 等再执行启动。"
      echo -e "${YELLOW}示例: open -e .env${NC}"
      exit 0
    else
      die "缺少 .env 且无 .env.example，无法继续。"
    fi
  fi
}

cmd_start() {
  check_mac
  check_docker
  ensure_env
  info "使用编排文件: $COMPOSE_FILE"
  info "拉取基础镜像并启动容器..."
  "${DC[@]}" pull mysql 2>/dev/null || true
  "${DC[@]}" up -d --build
  ok "已启动。"
  echo ""
  echo -e "  前端: ${GREEN}http://localhost:8081${NC}"
  echo -e "  后端: ${GREEN}http://localhost:8002${NC}  （文档: /docs）"
  echo -e "  MySQL 端口: ${GREEN}3308${NC}（宿主机）"
  echo ""
  echo "查看日志: ./docker-mac.sh logs"
}

cmd_stop() {
  check_docker
  "${DC[@]}" down
  ok "已停止（数据卷保留）。"
}

cmd_restart() {
  cmd_stop
  cmd_start
}

cmd_logs() {
  check_docker
  if [[ $# -gt 0 ]]; then
    "${DC[@]}" logs -f "$@"
  else
    "${DC[@]}" logs -f
  fi
}

cmd_rebuild() {
  check_mac
  check_docker
  ensure_env
  info "无缓存重建并启动..."
  "${DC[@]}" build --no-cache
  "${DC[@]}" up -d
  ok "重建完成。"
}

cmd_ps() {
  check_docker
  "${DC[@]}" ps -a
}

cmd_down_v() {
  check_docker
  echo -e "${RED}将删除容器及 MySQL 数据卷，确认请输入 yes:${NC} "
  read -r ans
  [[ "$ans" == "yes" ]] || { info "已取消"; exit 0; }
  "${DC[@]}" down -v
  ok "已停止并删除卷。"
}

usage() {
  sed -n '2,28p' "$0" | sed 's/^# \{0,1\}//'
}

main() {
  local sub="${1:-start}"
  shift || true
  case "$sub" in
    start|up)    cmd_start ;;
    stop|down)   cmd_stop ;;
    restart)     cmd_restart ;;
    logs)        cmd_logs "$@" ;;
    rebuild)     cmd_rebuild ;;
    ps|status)   cmd_ps ;;
    down-v)      cmd_down_v ;;
    help|-h|--help) usage ;;
    *)
      die "未知命令: $sub。运行: ./docker-mac.sh help"
      ;;
  esac
}

main "$@"
