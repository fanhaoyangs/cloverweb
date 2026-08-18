#!/usr/bin/env bash
# CloverWeb CVM 一次性初始化
# 支持: Ubuntu 22.04/24.04 (apt) / OpenCloudOS / CentOS / RHEL / Rocky (dnf)
# 支持: 裸机 / 宝塔面板 (BT-Panel) 共存
# 用法: sudo DB_PASS=<密码> [CERTBOT_EMAIL=<邮箱>] bash deploy/setup-server.sh
# 退出: 0=成功 / 1=失败
set -euo pipefail

APP_DIR=/opt/cloverweb
APP_USER=cloverweb
DEPLOY_USER=cloverweb-deploy
DB_NAME=cloverweb
DB_USER=cloverweb
DB_PASS="${DB_PASS:?ERROR: 必须 export DB_PASS=<数据库密码>}"
CERTBOT_EMAIL="${CERTBOT_EMAIL:-}"

# ---- 0. 发行版 / 宝塔检测 ----
. /etc/os-release 2>/dev/null || { echo "ERROR: 不支持的操作系统"; exit 1; }
PKG=""; case "${ID:-}" in
  ubuntu|debian) PKG=apt ;;
  opencloudos|centos|rhel|rocky|almalinux|fedora) PKG=dnf ;;
  *) echo "ERROR: 不支持的发行版 ${ID:-?}"; exit 1 ;;
esac

BT_PANEL=false
[[ -d /www/server/panel ]] && BT_PANEL=true

if $BT_PANEL; then
  NGX_BIN=/www/server/nginx/sbin/nginx
  NGX_VHOST=/www/server/panel/vhost/nginx
  NGX_CONF=/www/server/nginx/conf/nginx.conf
  echo "==> 检测到宝塔面板（${PRETTY_NAME}）"
else
  NGX_BIN=$(command -v nginx || echo /usr/sbin/nginx)
  NGX_VHOST=/etc/nginx/sites-available
  NGX_CONF=/etc/nginx/nginx.conf
fi
echo "==> 包管理器: $PKG / 宝塔: $BT_PANEL"

# ---- 1. 系统基础依赖 ----
echo "==> [1/9] 系统基础依赖"
case $PKG in
  apt)
    apt-get update -qq
    apt-get install -y -qq curl rsync ca-certificates gnupg lsb-release \
      python3 python3-venv python3-pip
    ;;
  dnf)
    dnf install -y -q curl rsync ca-certificates gnupg \
      python3 python3-pip
    # 尝试启用 python3.11 module（OpenCloudOS 8/9 都支持）
    dnf module -y enable python311 2>/dev/null || dnf module -y switch-to python311 2>/dev/null || true
    # venv 包名按 Python 主版本动态探测（OCL9 + Python 3.11 → python3.11-venv）
    PY_MM=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "3.11")
    dnf install -y -q "python${PY_MM}-venv" 2>/dev/null || dnf install -y -q python3-venv 2>/dev/null || \
      { echo "    ⚠ python3-venv 安装失败，尝试 ensurepip 方式"; python3 -m ensurepip --upgrade 2>/dev/null || true; }
    ;;
esac

# ---- 2. PostgreSQL 16 ----
echo "==> [2/9] PostgreSQL 16"
# 再次清理缓存（之前 PG 那步的脏缓存）
dnf clean all -q 2>/dev/null || true
rm -f /var/run/dnf.pid 2>/dev/null || true

case $PKG in
  apt)
    if ! apt-cache show postgresql-16 >/dev/null 2>&1; then
      install -d /usr/share/postgresql-common/pgdg
      curl -fsS https://www.postgresql.org/media/keys/ACCC4CF8.asc \
        -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc
      echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list
      apt-get update -qq
    fi
    apt-get install -y -qq postgresql-16
    PG_DATA=/var/lib/postgresql/16/main
    PG_CONF=/etc/postgresql/16/main
    ;;
  dnf)
    dnf install -y -q https://download.postgresql.org/pub/repos/yum/\
reporpms/EL-$(rpm -E '%{rhel}')-x86_64/pgdg-redhat-repo-latest.noarch.rpm
    dnf -qy module disable postgresql 2>/dev/null || true
    dnf install -y -q postgresql16-server postgresql16-contrib
    # 初始化（仅首次）
    PG_DATA=/var/lib/pgsql/16/data
    PG_CONF=/var/lib/pgsql/16/data
    [[ ! -f $PG_DATA/PG_VERSION ]] && /usr/pgsql-16/bin/postgresql-16-setup initdb
    ;;
esac

# 启动 PG（先 enable 再 start；RHEL 立即启动，Debian/Ubuntu 装完就启动了）
systemctl enable postgresql 2>/dev/null || systemctl enable postgresql-16
systemctl start postgresql 2>/dev/null || systemctl start postgresql-16

# 2C2G 保守参数
cat >${PG_CONF}/postgresql.conf.d/cloverweb.conf 2>/dev/null || \
  cat >${PG_CONF}/cloverweb.conf <<'EOF'
# CloverWeb 2C2G 调优
shared_buffers = 256MB
effective_cache_size = 768MB
work_mem = 4MB
max_connections = 60
EOF
case $PKG in
  apt) cat >/etc/postgresql/16/main/conf.d/cloverweb.conf <<'EOF'
# CloverWeb 2C2G 调优
shared_buffers = 256MB
effective_cache_size = 768MB
work_mem = 4MB
max_connections = 60
EOF
  ;;
esac
systemctl reload postgresql 2>/dev/null || systemctl reload postgresql-16 2>/dev/null || true

# ---- 3. DB 与用户 ----
echo "==> [3/9] 数据库 $DB_NAME / 用户 $DB_USER"
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" 2>/dev/null | grep -q 1 || \
  sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" 2>/dev/null | grep -q 1 || \
  sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER ENCODING 'UTF8';"

# ---- 4. 应用用户 / 目录 / 部署用户 ----
echo "==> [4/9] 应用用户与目录"
id -u $APP_USER >/dev/null 2>&1 || useradd -r -m -d $APP_DIR -s /usr/sbin/nologin $APP_USER
mkdir -p $APP_DIR/{backend,web,deploy}
cp -r "$(dirname "$0")"/. $APP_DIR/deploy/

# CI 部署用户
id -u $DEPLOY_USER >/dev/null 2>&1 || useradd -r -m -s /bin/bash $DEPLOY_USER
install -d -m 700 -o $DEPLOY_USER -g $DEPLOY_USER /home/$DEPLOY_USER/.ssh
touch /home/$DEPLOY_USER/.ssh/authorized_keys
chown $DEPLOY_USER:$DEPLOY_USER /home/$DEPLOY_USER/.ssh/authorized_keys
chmod 600 /home/$DEPLOY_USER/.ssh/authorized_keys
cat >/etc/sudoers.d/$DEPLOY_USER <<EOF
$DEPLOY_USER ALL=(root) NOPASSWD: /bin/bash $APP_DIR/deploy/deploy.sh *
EOF
chmod 440 /etc/sudoers.d/$DEPLOY_USER

# ---- 5. Python venv ----
echo "==> [5/9] Python 虚拟环境"
PY=$(command -v python3.11 || command -v python3 || command -v python3.10 || echo "python3")
echo "    使用 Python: $($PY --version 2>&1) ($PY)"

# 优先尝试 dnf 装 venv（如果还缺）
PY_MM=$($PY -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "3.11")
if ! $PY -m venv --help >/dev/null 2>&1; then
  echo "    尝试 dnf install python${PY_MM}-venv"
  dnf install -y -q "python${PY_MM}-venv" 2>&1 | tail -3 || true
fi

# 创建 venv
if $PY -m venv $APP_DIR/backend/venv 2>&1 | tail -3; then
  echo "    ✓ venv 创建成功"
else
  echo "    尝试以 $APP_USER 创建"
  sudo -u $APP_USER $PY -m venv $APP_DIR/backend/venv 2>&1 | tail -3 || true
fi
[[ -f $APP_DIR/backend/venv/bin/python ]] || \
  { err "venv 创建失败（$APP_DIR/backend/venv/bin/python 不存在）"; exit 1; }

# ---- 6. backend/.env（首次生成，不覆盖） ----
echo "==> [6/9] backend/.env"
if [[ ! -f $APP_DIR/backend/.env ]]; then
  SECRET=$(openssl rand -hex 32 2>/dev/null || head -c32 /dev/urandom | xxd -p -c64)
  cat >$APP_DIR/backend/.env <<EOF
DJANGO_SETTINGS_MODULE=cloverweb.settings.prod
DJANGO_SECRET_KEY=$SECRET
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASS
DB_HOST=127.0.0.1
DB_PORT=5432

# 腾讯云 COS（UEditorPlus 上传；必填才能传图）
COS_SECRET_ID=
COS_SECRET_KEY=
COS_REGION=ap-shanghai
COS_BUCKET=
COS_BASE_URL=https://images.communitygarden.org.cn

SITE_URL=https://communitygarden.org.cn

# 飞书 OAuth（CMS 登录）
FEISHU_APP_ID=
FEISHU_APP_SECRET=
FEISHU_REDIRECT_URI=https://communitygarden.org.cn/api/auth/feishu/callback/
FEISHU_ALLOWED_OPEN_IDS=
EOF
  echo "    ⚠ 已生成 $APP_DIR/backend/.env，请手动补 COS_SECRET_ID/KEY/BUCKET 等凭证"
fi
chown $APP_USER:$APP_USER $APP_DIR/backend/.env
chmod 600 $APP_DIR/backend/.env

# ---- 7. systemd 服务 ----
echo "==> [7/9] systemd 服务 cloverweb"
cp $APP_DIR/deploy/systemd/cloverweb.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable cloverweb

# ---- 8. Nginx 站点 ----
echo "==> [8/9] Nginx 站点 cloverweb"
# 备份现有主域 vhost（如有）
[[ -f $NGX_VHOST/communitygarden.org.cn.conf ]] && \
  cp $NGX_VHOST/communitygarden.org.cn.conf $NGX_VHOST/disabled/communitygarden.org.cn.conf.bak-$(date +%Y%m%d) 2>/dev/null || true

# 检测宝塔已有证书路径
BT_CERT=""
BT_KEY=""
if $BT_PANEL && [[ -f /www/server/panel/vhost/cert/communitygarden.org.cn/fullchain.pem ]]; then
  BT_CERT=/www/server/panel/vhost/cert/communitygarden.org.cn/fullchain.pem
  BT_KEY=/www/server/panel/vhost/cert/communitygarden.org.cn/privkey.pem
  echo "    复用宝塔已有证书: $BT_CERT"
fi

# 生成 vhost（如果有宝塔证书则直接出 HTTPS+重定向；否则 HTTP-only，certbot 后续升级）
if [[ -n "$BT_CERT" ]]; then
  cat > $NGX_VHOST/cloverweb.conf <<NGINX_EOF
# CloverWeb vhost (BT-Panel 模式，HTTPS + 重定向)
server {
    listen 80;
    server_name communitygarden.org.cn www.communitygarden.org.cn;
    location /.well-known/acme-challenge/ { root /var/www/html; }
    location / { return 301 https://\$host\$request_uri; }
}
server {
    listen 443 ssl http2;
    server_name communitygarden.org.cn www.communitygarden.org.cn;

    ssl_certificate     $BT_CERT;
    ssl_certificate_key $BT_KEY;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    root /opt/cloverweb/web;
    index index.html;

    location / {
        try_files \$uri \$uri/ /index.html;
    }
    location /assets/ { expires 30d; add_header Cache-Control "public, immutable"; }
    location /UEditorPlus/ { expires 7d; }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        client_max_body_size 220m;
        proxy_read_timeout 120s;
    }
    location /django-admin/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    location /static/ {
        alias /opt/cloverweb/backend/staticfiles/;
        expires 7d;
    }

    gzip on;
    gzip_types text/plain text/css application/json application/javascript image/svg+xml;
    gzip_min_length 1k;
}
NGINX_EOF
else
  # HTTP-only，certbot --nginx 后续会加 443 段
  cp $APP_DIR/deploy/nginx/cloverweb.conf $NGX_VHOST/cloverweb.conf
fi

# 宝塔主配置 include 检查
if $BT_PANEL; then
  grep -q "include.*vhost/nginx/\*\.conf" $NGX_CONF || \
    echo -e "\n    include $NGX_VHOST/*.conf;" >> $NGX_CONF
else
  ln -sf $NGX_VHOST/cloverweb.conf /etc/nginx/sites-enabled/cloverweb.conf
  rm -f /etc/nginx/sites-enabled/default
fi
$NGX_BIN -t && $NGX_BIN -s reload

# ---- 9. HTTPS 证书 ----
echo "==> [9/9] HTTPS 证书"
if [[ -n "$BT_CERT" ]]; then
  echo "    ✓ 已复用宝塔证书，跳过 certbot"
else
  if [[ -n "$CERTBOT_EMAIL" ]]; then
    case $PKG in
      apt) apt-get install -y -qq certbot python3-certbot-nginx ;;
      dnf) dnf install -y -q certbot python3-certbot-nginx ;;
    esac
    if $BT_PANEL; then
      # 宝塔环境 nginx 插件会改错文件，用 webroot
      mkdir -p /var/www/html/.well-known/acme-challenge
      certbot certonly --webroot -w /var/www/html \
        -d communitygarden.org.cn -d www.communitygarden.org.cn \
        --non-interactive --agree-tos -m "$CERTBOT_EMAIL" || \
        echo "    ⚠ certbot 失败，请到宝塔面板 → 网站 → 设置 → SSL → Let's Encrypt 申请后手工改 vhost 加 443 段"
    else
      certbot --nginx -d communitygarden.org.cn -d www.communitygarden.org.cn \
        --non-interactive --agree-tos -m "$CERTBOT_EMAIL" --redirect || \
        echo "    ⚠ certbot 失败，请手动 certbot --nginx -d communitygarden.org.cn"
    fi
  else
    echo "    ⚠ 未提供 CERTBOT_EMAIL，跳过证书申请；请到宝塔面板/手动 certbot 申请后填到 vhost"
  fi
fi

echo
echo "=========================================="
echo "  初始化完成"
echo "  - 应用:   $APP_DIR"
echo "  - 部署:   https://communitygarden.org.cn"
echo "  - 后台:   https://communitygarden.org.cn/admin/login"
echo "  - 必做:"
echo "    1. $APP_DIR/backend/.env 补 COS 凭证"
echo "    2. /home/$DEPLOY_USER/.ssh/authorized_keys 追加 GitHub Actions 公钥"
echo "    3. GitHub Secrets: SSH_HOST/SSH_USER=$DEPLOY_USER/SSH_PRIVATE_KEY"
echo "    4. 创建 superuser: 首次部署后"
echo "       sudo -u $APP_USER $APP_DIR/backend/venv/bin/python \\"
echo "         $APP_DIR/backend/manage.py createsuperuser"
echo "=========================================="
