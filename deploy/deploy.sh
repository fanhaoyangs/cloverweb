#!/usr/bin/env bash
# CloverWeb 每次部署脚本（由 GitHub Actions 调用，在 CVM 上执行）
# 用法: sudo bash /opt/cloverweb/deploy/deploy.sh /tmp/cloverweb-deploy.tar.gz
set -euo pipefail

APP_DIR=/opt/cloverweb
APP_USER=cloverweb
TARBALL="${1:-/tmp/cloverweb-deploy.tar.gz}"
STAGE=$(mktemp -d /tmp/cloverweb-stage.XXXXXX)

echo "==> [1/6] 解包 $TARBALL"
tar -xzf "$TARBALL" -C "$STAGE"
test -d "$STAGE/backend" && test -d "$STAGE/web"

echo "==> [2/6] 停止服务"
systemctl stop cloverweb || true

echo "==> [3/6] 同步代码"
# 前端产物全量替换（清掉旧 hash 产物）
rsync -a --delete "$STAGE/web/" "$APP_DIR/web/"
# 后端源码同步，保留 venv / .env / staticfiles / media
rsync -a --delete \
  --exclude 'venv/' \
  --exclude '.env' \
  --exclude 'db.sqlite3' \
  --exclude 'staticfiles/' \
  --exclude 'media/' \
  "$STAGE/backend/" "$APP_DIR/backend/"
mkdir -p "$APP_DIR"/backend/{staticfiles,media}
chown -R $APP_USER:$APP_USER "$APP_DIR"/backend/{staticfiles,media}

echo "==> [4/6] 安装依赖"
sudo -u $APP_USER "$APP_DIR/backend/venv/bin/pip" install -q -r "$APP_DIR/backend/requirements.txt"

echo "==> [5/6] 数据库迁移 + 收集静态文件"
# sudo 会重置环境，.env 在子 shell 内以应用用户加载
sudo -u $APP_USER bash -c "cd $APP_DIR/backend && set -a && source .env && set +a && \
  venv/bin/python manage.py migrate --noinput && \
  venv/bin/python manage.py collectstatic --noinput --clear"

echo "==> [6/6] 启动服务"
systemctl start cloverweb
sleep 2
systemctl is-active cloverweb && echo "==> 部署完成"

rm -rf "$STAGE" "$TARBALL"
