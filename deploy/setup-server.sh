#!/usr/bin/env bash
# CloverWeb 服务器一次性初始化（Ubuntu 22.04/24.04，2C2G CVM）
# 用法: sudo bash deploy/setup-server.sh
# 包含：PostgreSQL 16 + Nginx + Python venv + systemd + Nginx 站点
set -euo pipefail

APP_DIR=/opt/cloverweb
APP_USER=cloverweb
DB_NAME=cloverweb
DB_USER=cloverweb
DB_PASS="${DB_PASS:?请先 export DB_PASS=<数据库密码>}"

echo "==> [1/9] 系统依赖"
apt-get update -qq
apt-get install -y -qq nginx rsync curl ca-certificates gnupg

echo "==> [2/9] PostgreSQL 16（PGDG）"
if ! apt-cache show postgresql-16 >/dev/null 2>&1; then
  install -d /usr/share/postgresql-common/pgdg
  curl -fsS https://www.postgresql.org/media/keys/ACCC4CF8.asc \
    -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc
  echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
    > /etc/apt/sources.list.d/pgdg.list
  apt-get update -qq
fi
apt-get install -y -qq postgresql-16

echo "==> [3/9] 数据库与用户"
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER ENCODING 'UTF8';"

# 2C2G 保守内存参数（与系统其他服务共存）
cat >/etc/postgresql/16/main/conf.d/cloverweb.conf <<'EOF'
shared_buffers = 256MB
effective_cache_size = 768MB
max_connections = 60
EOF
systemctl restart postgresql

echo "==> [4/9] 应用用户与目录"
id -u $APP_USER >/dev/null 2>&1 || useradd -r -m -d $APP_DIR -s /usr/sbin/nologin $APP_USER
mkdir -p $APP_DIR/{backend,web,deploy}
cp -r "$(dirname "$0")"/. $APP_DIR/deploy/

# CI 部署用户（SSH 登录用，与应用运行用户分离）
DEPLOY_USER=cloverweb-deploy
id -u $DEPLOY_USER >/dev/null 2>&1 || useradd -r -m -s /bin/bash $DEPLOY_USER
install -d -m 700 -o $DEPLOY_USER -g $DEPLOY_USER /home/$DEPLOY_USER/.ssh
touch /home/$DEPLOY_USER/.ssh/authorized_keys
chown $DEPLOY_USER:$DEPLOY_USER /home/$DEPLOY_USER/.ssh/authorized_keys
chmod 600 /home/$DEPLOY_USER/.ssh/authorized_keys
# 免密 sudo 仅限部署命令
cat >/etc/sudoers.d/cloverweb-deploy <<EOF
$DEPLOY_USER ALL=(root) NOPASSWD: /bin/bash $APP_DIR/deploy/deploy.sh *
EOF
chmod 440 /etc/sudoers.d/cloverweb-deploy
echo "    请将 GitHub Actions 公钥追加到 /home/$DEPLOY_USER/.ssh/authorized_keys"

echo "==> [5/9] Python 虚拟环境"
PY=$(command -v python3.12 || command -v python3.13 || echo /usr/bin/python3)
apt-get install -y -qq python3-venv python3-pip
sudo -u $APP_USER $PY -m venv $APP_DIR/backend/venv

echo "==> [6/9] backend/.env（首次生成，之后 CI 不覆盖）"
if [ ! -f $APP_DIR/backend/.env ]; then
  SECRET=$(openssl rand -hex 32 2>/dev/null || head -c32 /dev/urandom | xxd -p -c64)
  cat >$APP_DIR/backend/.env <<EOF
DJANGO_SETTINGS_MODULE=cloverweb.settings.prod
DJANGO_SECRET_KEY=$SECRET
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASS
DB_HOST=127.0.0.1
DB_PORT=5432

# 腾讯云 COS（UEditorPlus 上传）
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
  echo "    已生成 $APP_DIR/backend/.env，请手动补 COS_SECRET_ID/KEY/BUCKET 等凭证"
fi
chown $APP_USER:$APP_USER $APP_DIR/backend/.env
chmod 600 $APP_DIR/backend/.env

echo "==> [7/9] systemd 服务"
cp $APP_DIR/deploy/systemd/cloverweb.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable cloverweb

echo "==> [8/9] Nginx 站点"
cp $APP_DIR/deploy/nginx/cloverweb.conf /etc/nginx/sites-available/cloverweb
ln -sf /etc/nginx/sites-available/cloverweb /etc/nginx/sites-enabled/cloverweb
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo "==> [9/9] HTTPS 证书（certbot，需域名解析已指向本机）"
apt-get install -y -qq certbot python3-certbot-nginx
certbot --nginx -d communitygarden.org.cn -d www.communitygarden.org.cn --non-interactive --agree-tos \
  -m "${CERTBOT_EMAIL:?请先 export CERTBOT_EMAIL=<你的邮箱>}" --redirect || \
  echo "    证书签发失败（可稍后手动执行 certbot --nginx -d communitygarden.org.cn）"

echo "==> 初始化完成。下一步：在 GitHub 仓库配置 Secrets 后触发 deploy workflow"
