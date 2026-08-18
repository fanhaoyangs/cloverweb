#!/usr/bin/env bash
# CloverWeb CVM 部署 - 预检（环境检测 + 冲突检查 + workhour 存活验证）
# 用法: sudo bash deploy/preflight.sh
# 退出码: 0=可继续 / 1=需先解决问题 / 2=警告（可继续但不推荐）
set -uo pipefail

RED='\033[0;31m'; GRN='\033[0;32m'; YEL='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GRN}[OK]${NC} $*"; }
warn() { echo -e "${YEL}[WARN]${NC} $*"; FAIL=1; }
err()  { echo -e "${RED}[FAIL]${NC} $*"; FAIL=1; }
FAIL=0

echo "=========================================="
echo "  CloverWeb 部署预检"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

# ---- 1. 发行版 ----
echo
echo "## 1. 操作系统"
. /etc/os-release 2>/dev/null
echo "  发行版: ${PRETTY_NAME:-未知}"
echo "  ID: ${ID:-?} / VERSION_ID: ${VERSION_ID:-?}"
if [[ "${ID:-}" == "opencloudos" || "${ID:-}" == "centos" || "${ID:-}" == "rhel" || "${ID:-}" == "rocky" || "${ID:-}" == "almalinux" ]]; then
  ok "RHEL 系，setup-server.sh 会走 dnf 分支"
elif [[ "${ID:-}" == "ubuntu" || "${ID:-}" == "debian" ]]; then
  ok "Debian 系，setup-server.sh 会走 apt 分支"
else
  warn "未识别发行版，需手动确认包管理器"
fi

# ---- 2. 包管理器 ----
echo
echo "## 2. 包管理器"
if command -v dnf >/dev/null; then
  echo "  dnf: $(dnf --version | head -1)"
elif command -v yum >/dev/null; then
  echo "  yum: $(yum --version | head -1)"
fi
if command -v apt >/dev/null; then echo "  apt: $(apt --version | head -1)"; fi

# ---- 3. 宝塔面板 ----
echo
echo "## 3. 宝塔面板"
if [[ -d /www/server/panel ]]; then
  BT_VER=$(cat /www/server/panel/BT-Panel 2>/dev/null || cat /www/server/panel/VERSION 2>/dev/null || echo "未知")
  ok "宝塔面板已安装（版本: $BT_VER）"
  echo "  主 nginx: /www/server/nginx/sbin/nginx"
  echo "  vhost 目录: /www/server/panel/vhost/nginx/"
  echo "  证书目录: /www/server/panel/vhost/cert/"
  NGX_BIN=/www/server/nginx/sbin/nginx
  NGX_VHOST=/www/server/panel/vhost/nginx
else
  warn "未检测到宝塔面板，将按标准 /etc/nginx 部署"
  NGX_BIN=$(command -v nginx || echo /usr/sbin/nginx)
  NGX_VHOST=/etc/nginx/sites-available
fi

# ---- 4. 关键端口占用 ----
echo
echo "## 4. 端口占用（必须 80/443/8000 三个端口的归属）"
ss -tlnp 2>/dev/null | awk 'NR>1 {print $4, $6}' | grep -E ":(80|443|8000|3000|5000|5001)\b" | while read line; do
  echo "  $line"
done
echo
for port in 80 443; do
  if ss -tlnp 2>/dev/null | grep -qE ":${port}\b.*nginx"; then
    ok ":${port} 由 nginx 占用（正确）"
  else
    warn ":${port} 未被 nginx 监听（部署后 Nginx 不会自启）"
  fi
done
if ss -tlnp 2>/dev/null | grep -qE ":8000\b"; then
  err ":8000 已被占用，新部署的 gunicorn 无法绑定"
  ss -tlnp 2>/dev/null | grep ":8000"
fi
if ss -tlnp 2>/dev/null | grep -qE ":5000\b|:3000\b"; then
  ok ":5000 / :3000 未残留（旧站点已清理）"
fi

# ---- 5. workhour 存活（红线检查） ----
echo
echo "## 5. workhour_app 存活（绝对不能动）"
if ss -tlnp 2>/dev/null | grep -qE ":5001\b"; then
  HTTP=$(curl -fsS -o /dev/null -w '%{http_code}' http://127.0.0.1:5001/ 2>/dev/null || echo "000")
  if [[ "$HTTP" == "200" || "$HTTP" == "302" ]]; then
    ok "workhour_app 正常 (HTTP $HTTP)"
  else
    warn "workhour_app 在监听但 HTTP $HTTP（异常）"
  fi
else
  warn "workhour_app 未监听（可能未运行，与 cloverweb 无直接冲突）"
fi
if [[ -d /www/wwwroot/workhour_app ]]; then
  ok "workhour 目录存在: /www/wwwroot/workhour_app"
else
  warn "workhour 目录不存在（部署环境异常）"
fi

# ---- 6. 残留冲突 ----
echo
echo "## 6. 残留冲突检查"
if [[ -d /opt/cloverweb ]]; then
  err "/opt/cloverweb 已存在（部署会先备份后覆盖，但请确认无未提交内容）"
  ls -la /opt/cloverweb/ 2>/dev/null | head -5
else
  ok "/opt/cloverweb 不存在（干净环境）"
fi
if id cloverweb >/dev/null 2>&1; then
  warn "cloverweb 用户已存在（可能是上次部署残留）"
fi
if id cloverweb-deploy >/dev/null 2>&1; then
  warn "cloverweb-deploy 用户已存在"
fi
if [[ -f /opt/cloverweb/backend/.env ]]; then
  warn "backend/.env 已存在（不会覆盖，但需检查 COS 凭证是否需要更新）"
fi

# ---- 7. PG 状态 ----
echo
echo "## 7. PostgreSQL 状态"
if command -v psql >/dev/null; then
  PG_VER=$(psql --version | awk '{print $3}')
  ok "psql 已安装: $PG_VER"
  sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='cloverweb'" 2>/dev/null | grep -q 1 && \
    warn "数据库 cloverweb 已存在" || ok "数据库 cloverweb 未建（干净）"
else
  warn "psql 未安装（setup-server.sh 会装 PGDG PG16）"
fi

# ---- 8. Python 版本 ----
echo
echo "## 8. Python"
PY3=$(command -v python3 || echo "")
if [[ -n "$PY3" ]]; then
  PY_VER=$($PY3 --version 2>&1)
  echo "  $PY3: $PY_VER"
  if $PY3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
    ok "Python >= 3.10（Django 5 要求）"
  else
    warn "Python < 3.10，需要从 dnf module 或源码安装 3.11+"
  fi
else
  err "python3 不存在"
fi

# ---- 9. 总结 ----
echo
echo "=========================================="
if [[ $FAIL -eq 0 ]]; then
  echo -e "${GRN}预检通过，可以继续运行 setup-server.sh${NC}"
  exit 0
else
  echo -e "${YEL}预检发现问题（见上方 [WARN]/[FAIL]），请先解决再部署${NC}"
  exit 1
fi
