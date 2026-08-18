#!/usr/bin/env bash
# CloverWeb 每次部署脚本（由 GitHub Actions 调用，在 CVM 上执行）
# 用法: sudo bash /opt/cloverweb/deploy/deploy.sh /tmp/cloverweb-deploy.tar.gz
set -euo pipefail
# 关历史扩展（避免 .env 里含 ! 触发 bash 解析错误）
set +H

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
# 部署脚本 + 辅助工具同步到 /opt/cloverweb/deploy/（首次跑时这个目录可能不存在）
mkdir -p "$APP_DIR/deploy"
rsync -a "$STAGE/deploy/" "$APP_DIR/deploy/"
chmod +x "$APP_DIR/deploy/deploy.sh" "$APP_DIR/deploy/parse_env.py"
mkdir -p "$APP_DIR"/backend/{staticfiles,media}
chown -R $APP_USER:$APP_USER "$APP_DIR"/backend/{staticfiles,media}
# nginx 以 www 用户跑，需要可读 web/ 和 backend/staticfiles/
chmod 755 "$APP_DIR" "$APP_DIR/backend" "$APP_DIR/web"
chmod -R o+rX "$APP_DIR/web" "$APP_DIR/backend/staticfiles"

echo "==> [4/6] 安装依赖"
sudo -u $APP_USER "$APP_DIR/backend/venv/bin/pip" install -q -r "$APP_DIR/backend/requirements.txt"

echo "==> [5/6] 数据库迁移 + 收集静态文件"
# 关键：manage.py 默认是 dev settings（SQLite），CVM 上必须切到 prod（PostgreSQL）
# 用 python-dotenv 解析 .env（避免 bash source 遇到特殊字符炸）
# quoted 版：用于当前 shell eval（单引号包裹安全）
# unquoted 版：用于 sudo env 透传给子 shell（避免 'val' 当字符串）
ENV_EXPORTS_QUOTED=$("$APP_DIR/backend/venv/bin/python" "$APP_DIR/deploy/parse_env.py" "$APP_DIR/backend/.env" quoted)
ENV_EXPORTS_UNQUOTED=$("$APP_DIR/backend/venv/bin/python" "$APP_DIR/deploy/parse_env.py" "$APP_DIR/backend/.env" unquoted)
echo "  已加载 $(echo "$ENV_EXPORTS_QUOTED" | wc -l) 个环境变量"
# 当前 shell 加载（让 gunicorn / 后续命令也能看到）
export DJANGO_SETTINGS_MODULE=cloverweb.settings.prod
eval "$ENV_EXPORTS_QUOTED"
# 透传给 sudo 子 shell
# 已 set +H 关历史扩展，所以 DB_PASSWORD 里的 ! 不会触发 bash 扩展
sudo -u $APP_USER env $(echo "$ENV_EXPORTS_UNQUOTED" | sed 's/^export //') \
  DJANGO_SETTINGS_MODULE=cloverweb.settings.prod \
  bash -c "cd $APP_DIR/backend && \
    venv/bin/python manage.py migrate --noinput && \
    venv/bin/python manage.py collectstatic --noinput --clear && \
    venv/bin/python manage.py loaddata apps/team/fixtures/initial_sitepages.json 2>&1 | tail -3 || true"

echo "==> [6/6] 启动服务"
systemctl start cloverweb
sleep 2
systemctl is-active cloverweb && echo "==> 部署完成"

rm -rf "$STAGE" "$TARBALL"
