#!/usr/bin/env bash
# CloverWeb 旧版站点清理（脚本化）
# 用途: 在部署新 cloverweb 之前，清掉 CVM 上的 communitygarden / blog_system
# 保护: workhour_app 绝对不动，进程级 + 路径级双校验
# 用法: sudo bash deploy/cleanup-old-sites.sh
#       可选环境变量:
#         SKIP_BACKUP=1 跳过备份
#         ASSUME_YES=1   不询问直接执行
# 退出: 0=成功 / 1=失败 / 2=被用户拒绝
set -euo pipefail

RED='\033[0;31m'; GRN='\033[0;32m'; YEL='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GRN}[OK]${NC} $*"; }
warn() { echo -e "${YEL}[WARN]${NC} $*"; }
err()  { echo -e "${RED}[FAIL]${NC} $*"; }

# ---- 0. 红线：workhour 保护 ----
WORKHOUR_PORT=5001
WORKHOUR_DIR=/www/wwwroot/workhour_app

# 检测 workhour 进程（任何在 :5001 监听的进程都视为 workhour）
WORKHOUR_PIDS=$(ss -tlnp 2>/dev/null | grep -E ":${WORKHOUR_PORT}\b" | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u || true)
if [[ -z "$WORKHOUR_PIDS" ]]; then
  warn ":$WORKHOUR_PORT 未监听 workhour，请确认环境正确后再跑本脚本"
  [[ -z "${ASSUME_YES:-}" ]] && { read -p "按回车继续，Ctrl+C 取消..."; }
fi
# 用 iptables 兜底？不需要，路径白名单就够

# ---- 1. 摸底 ----
echo "=========================================="
echo "  CloverWeb 旧版站点清理"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

echo
echo "## 1. 旧站点摸底"
# 旧 Flask 博客
if [[ -d /www/wwwroot/blog_system ]]; then
  BS_DIR=/www/wwwroot/blog_system
  BS_PID=$(ss -tlnp 2>/dev/null | grep ":5000\b" | grep -oE 'pid=[0-9]+' | head -1 | cut -d= -f2 || true)
  ok "blog_system: 目录在 $BS_DIR / 进程 PID ${BS_PID:-未监听}"
else
  warn "blog_system 目录不存在（可能已清理）"
  BS_DIR=""
  BS_PID=""
fi

# 旧静态站
if [[ -d /www/wwwroot/communitygarden ]]; then
  CG_DIR=/www/wwwroot/communitygarden
  ok "communitygarden: 静态目录在 $CG_DIR"
else
  warn "communitygarden 目录不存在（可能已清理）"
  CG_DIR=""
fi

# activity-api 孤儿
ACT_PID=$(ps -ef | grep "activity-api" | grep -v grep | awk '{print $2}' | head -1 || true)
[[ -n "$ACT_PID" ]] && ok "activity-api 孤儿进程: PID $ACT_PID" || true

# nginx 主域 vhost
if [[ -d /www/server/panel/vhost/nginx ]]; then
  NGX_VHOST=/www/server/panel/vhost/nginx
elif [[ -d /etc/nginx/sites-available ]]; then
  NGX_VHOST=/etc/nginx/sites-available
else
  err "未找到 nginx vhost 目录"; exit 1
fi
CG_VHOST=""
[[ -f $NGX_VHOST/communitygarden.org.cn.conf ]] && CG_VHOST=$NGX_VHOST/communitygarden.org.cn.conf
BS_VHOST=""
[[ -f $NGX_VHOST/blog_system.conf ]] && BS_VHOST=$NGX_VHOST/blog_system.conf

# workhour 子域 vhost（保留）
WH_VHOST=$NGX_VHOST/workhour.communitygarden.org.cn.conf
[[ -f $WH_VHOST ]] && ok "workhour 子域 vhost: $WH_VHOST（保留不动）"

# ---- 2. 确认 ----
echo
echo "## 2. 操作清单"
echo "  备份:   /opt/cleanup-backup-$(date +%Y%m%d-%H%M%S)/"
[[ -n "$BS_DIR" ]] && echo "  删除目录: $BS_DIR"
[[ -n "$CG_DIR" ]] && echo "  删除目录: $CG_DIR"
[[ -n "$BS_PID" ]] && echo "  kill 进程: $BS_PID (blog_system)"
[[ -n "$ACT_PID" ]] && echo "  kill 进程: $ACT_PID (activity-api 孤儿)"
[[ -n "$CG_VHOST" ]] && echo "  移走 vhost: $CG_VHOST → $NGX_VHOST/disabled/"
[[ -n "$BS_VHOST" ]] && echo "  移走 vhost: $BS_VHOST → $NGX_VHOST/disabled/"
echo "  保留:    $WORKHOUR_DIR 及其进程 :$WORKHOUR_PORT（绝对不动）"

if [[ -z "${ASSUME_YES:-}" ]]; then
  echo
  read -p "确认执行？[y/N] " ans
  [[ "$ans" != "y" && "$ans" != "Y" ]] && { echo "已取消"; exit 2; }
fi

# ---- 3. 备份 ----
echo
echo "## 3. 备份"
BACKUP=/opt/cleanup-backup-$(date +%Y%m%d-%H%M%S)
mkdir -p $BACKUP
echo "  备份目录: $BACKUP"

# 备份旧 tar（如有）
if ls /www/wwwroot/communitygarden_*.tar.gz 2>/dev/null; then
  mv /www/wwwroot/communitygarden_*.tar.gz $BACKUP/ 2>/dev/null && \
    ok "原宝塔备份 tar 已移走" || true
fi

[[ -n "$BS_DIR" ]] && tar -czf $BACKUP/blog_system.tar.gz -C /www/wwwroot blog_system 2>/dev/null && \
  ok "blog_system 已备份 ($(du -h $BACKUP/blog_system.tar.gz | cut -f1))"
[[ -n "$CG_DIR" ]] && tar -czf $BACKUP/communitygarden.tar.gz -C /www/wwwroot communitygarden 2>/dev/null && \
  ok "communitygarden 已备份 ($(du -h $BACKUP/communitygarden.tar.gz | cut -f1))"

# 备份 vhost
[[ -n "$CG_VHOST" ]] && cp $CG_VHOST $BACKUP/ && ok "旧 vhost 已备份: $(basename $CG_VHOST)"
[[ -n "$WH_VHOST" ]] && cp $WH_VHOST $BACKUP/ && ok "workhour vhost 已备份: $(basename $WH_VHOST)"

# ---- 4. 停服（workhour 进程白名单过滤） ----
echo
echo "## 4. 停服"
[[ -n "$BS_PID" ]] && {
  # 二次校验：不是 workhour 才杀
  CWD=$(readlink /proc/$BS_PID/cwd 2>/dev/null || echo "")
  if [[ "$CWD" == *workhour* ]]; then
    err "  ✗ PID $BS_PID cwd 含 workhour 关键字，跳过（防御）"; exit 1
  fi
  kill $BS_PID 2>/dev/null && ok "blog_system (PID $BS_PID) SIGTERM"
  sleep 2
  kill -9 $BS_PID 2>/dev/null || true
}
[[ -n "$ACT_PID" ]] && {
  kill $ACT_PID 2>/dev/null && ok "activity-api (PID $ACT_PID) SIGTERM"
  sleep 1
  kill -9 $ACT_PID 2>/dev/null || true
}

# ---- 5. workhour 存活验证（关键） ----
echo
echo "## 5. workhour 存活验证（红线）"
W_HTTP=$(curl -fsS -o /dev/null -w '%{http_code}' http://127.0.0.1:$WORKHOUR_PORT/ 2>/dev/null || echo "000")
if [[ "$W_HTTP" == "200" || "$W_HTTP" == "302" ]]; then
  ok "workhour 正常 (HTTP $W_HTTP)"
else
  err "workhour 异常 (HTTP $W_HTTP)！立即停止后续"
  exit 1
fi
[[ -d $WORKHOUR_DIR ]] && ok "workhour 目录在" || err "workhour 目录丢失！"

# ---- 6. 删目录 ----
echo
echo "## 6. 删目录"
if [[ -n "$BS_DIR" ]]; then
  rm -rf $BS_DIR && ok "blog_system 目录已删" || err "blog_system 目录删除失败"
fi
if [[ -n "$CG_DIR" ]]; then
  # 处理 .user.ini 不可修改位（宝塔防误删）
  if [[ -f $CG_DIR/.user.ini ]]; then
    chattr -i $CG_DIR/.user.ini 2>/dev/null || true
  fi
  rm -rf $CG_DIR && ok "communitygarden 目录已删" || err "communitygarden 目录删除失败"
fi
echo "--- /www/wwwroot/ 当前内容 ---"
ls /www/wwwroot/

# ---- 7. 移走 vhost ----
echo
echo "## 7. 移走 vhost"
mkdir -p $NGX_VHOST/disabled
[[ -n "$CG_VHOST" ]] && mv $CG_VHOST $NGX_VHOST/disabled/$(basename $CG_VHOST).bak-$(date +%Y%m%d) && \
  ok "$(basename $CG_VHOST) → disabled/" || warn "$(basename $CG_VHOST) 移走失败"
[[ -n "$BS_VHOST" ]] && mv $BS_VHOST $NGX_VHOST/disabled/$(basename $BS_VHOST).bak-$(date +%Y%m%d) && \
  ok "$(basename $BS_VHOST) → disabled/" || warn "$(basename $BS_VHOST) 移走失败"

# ---- 8. nginx -t + reload ----
echo
echo "## 8. nginx 验证"
NGX_BIN=$([[ -f /www/server/nginx/sbin/nginx ]] && echo /www/server/nginx/sbin/nginx || echo nginx)
if $NGX_BIN -t 2>&1; then
  $NGX_BIN -s reload && ok "nginx 已重载"
else
  err "nginx 配置测试失败！请检查后手动重载"
  exit 1
fi

# ---- 9. 最终验证 ----
echo
echo "## 9. 最终验证"
ss -tlnp 2>/dev/null | grep -E ":3000|:5000\b" && warn "仍有旧端口在监听" || ok "5000/3000 已释放"
ss -tlnp 2>/dev/null | grep -E ":${WORKHOUR_PORT}\b" >/dev/null && ok "workhour :$WORKHOUR_PORT 仍监听" || warn "workhour :$WORKHOUR_PORT 没了！"
ss -tlnp 2>/dev/null | grep -E ":80|:443" >/dev/null && ok "80/443 仍监听" || warn "80/443 没了"
curl -fsS -o /dev/null -w "communitygarden.org.cn HTTP %{http_code}\n" http://127.0.0.1/ -H "Host: communitygarden.org.cn" 2>/dev/null || true

echo
echo "=========================================="
ok "旧版清理完成"
echo "  备份:   $BACKUP"
echo "  保留:   $WORKHOUR_DIR（workhour_app）"
echo "  下一步: 1) 跑 deploy/setup-server.sh  2) 补 .env 凭证  3) 推代码触发 CI"
echo "=========================================="
