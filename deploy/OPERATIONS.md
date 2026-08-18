# CloverWeb 部署操作手册

> 本手册配套 `deploy/` 目录下的脚本（`setup-server.sh` / `deploy.sh`）和 `.github/workflows/deploy.yml`。
> 适用：Ubuntu 22.04/24.04 的 2 核 2G 腾讯云 CVM，域名 `communitygarden.org.cn`。

## 目录

1. [前置准备](#1-前置准备)
2. [第 1 步：在 CVM 上执行初始化脚本](#2-第-1-步在-cvm-上执行初始化脚本)
3. [第 2 步：把项目推送到 GitHub 并配置 Secrets](#3-第-2-步把项目推送到-github-并配置-secrets)
4. [第 3 步：补全 CVM 上的 `.env` 凭证 + 创建 superuser](#4-第-3-步补全-cvm-上的-env-凭证--创建-superuser)
5. [第 4 步：触发首次部署并验证](#5-第-4-步触发首次部署并验证)
6. [日常运维速查](#6-日常运维速查)
7. [常见问题](#7-常见问题)

---

## 1. 前置准备

### 1.1 需要准备的东西

| 项目 | 用途 | 来源 |
|---|---|---|
| 腾讯云 CVM | 2C2G，运行应用 | 已买好 |
| 域名 `communitygarden.org.cn` | 站点访问 | 已解析到 CVM 公网 IP |
| 腾讯云 COS 桶 | UEditorPlus 媒体存储 | 需新建（见 1.2） |
| 飞书自建应用 AppID/Secret | CMS 飞书登录 | 可后补，先用 superuser 登录 |
| GitHub 仓库 | 代码托管 + CI | `fanhaoyangs/cloverweb`（如未建，先建） |
| 一个本地 SSH 公钥 | CI 部署 CVM | `ssh-keygen -t ed25519` |

### 1.2 创建 COS 桶（首次需要）

1. 腾讯云控制台 → 对象存储 → 创建桶：
   - 名称：例如 `images-community-1300000000`（必须以 APPID 结尾）
   - 地域：与 CVM 同区（上海：`ap-shanghai`）
   - 权限：**公有读私有写**
   - CORS：跨域规则加一条 `*`、允许 `GET/POST/HEAD/PUT`
2. 绑定自定义 CDN 域名（已有 `images.communitygarden.org.cn` 跳过）
3. 访问管理 → API 密钥管理 → 新建 SecretId/SecretKey，**这两串只显示一次，立即复制保存**

### 1.3 把域名解析到 CVM

- 腾讯云 DNSPod：`communitygarden.org.cn` 和 `www` 都加 A 记录指向 CVM 公网 IP
- 等 DNS 生效（一般 5 分钟内，可用 `dig communitygarden.org.cn` 验证）

---

## 2. 第 1 步：在 CVM 上执行初始化脚本

> 此步只在首次部署新机器时执行一次。

### 2.1 SSH 登录 CVM

```bash
ssh root@<你的 CVM 公网 IP>
# 或在腾讯云控制台 → 实例 → 登录 → 立即登录
```

### 2.2 上传项目代码

代码可以**先不上传**，setup-server.sh 自带 `cp -r "$(dirname "$0")"` 拷贝 deploy 目录；推荐从本地用 scp 把整个 `deploy/` 目录传过去：

```bash
# 本地执行（非 CVM）
scp -r deploy/ root@<CVM_IP>:/opt/cloverweb-source/
```

> 也可以直接在 CVM 上 `git clone` 你的仓库后再单独 `cd deploy && bash setup-server.sh`。
> 关键是要让 `setup-server.sh` 和它的同级 `systemd/` `nginx/` 目录能被复制到 `/opt/cloverweb/deploy/`。

### 2.3 执行初始化脚本

```bash
# 必须在 /opt/cloverweb-source/deploy 目录下或把 deploy 目录放到 $APP_DIR/deploy
cd /opt/cloverweb-source/deploy

# 必传两个环境变量
export DB_PASS="<一个强密码，建议 16 位以上含大小写数字>"
export CERTBOT_EMAIL="<你的邮箱，Let's Encrypt 通知用>"

sudo bash setup-server.sh
```

#### 脚本会做的事（共 9 步，约 5-15 分钟）

1. 装 nginx / rsync / curl / gnupg
2. 装 PostgreSQL 16（从 PGDG 源）
3. 建 `cloverweb` 数据库 + 用户，配 2C2G 保守参数
4. 建 `cloverweb` 应用用户 + `cloverweb-deploy` 部署用户 + sudoers 白名单
5. 建 Python 虚拟环境
6. 生成 `/opt/cloverweb/backend/.env`（首次含随机 SECRET_KEY，**不会覆盖**）
7. 注册 systemd 服务 `cloverweb`（开机自启）
8. 配置 Nginx 站点 `cloverweb`（80 端口，certbot 会自动升级 443）
9. 申请 Let's Encrypt 证书 + 自动 HTTPS 重定向

### 2.4 注意事项

- **DB_PASS 必须 export 进去**，脚本用 `${DB_PASS:?}` 强校验，否则直接报错退出
- **CERTBOT_EMAIL 同理**，否则 certbot 签证书会失败
- 脚本结束时会说"请将 GitHub Actions 公钥追加到 /home/cloverweb-deploy/.ssh/authorized_keys"，**这步先放着**（第 2 步才做）
- 如果 certbot 因为 DNS 没生效签失败，再次跑：`sudo certbot --nginx -d communitygarden.org.cn -d www.communitygarden.org.cn`

### 2.5 验证初始化结果

```bash
# 服务进程
systemctl status cloverweb  # 应该是 inactive，因为还没有代码部署
systemctl status nginx      # active
systemctl status postgresql # active

# 数据库
sudo -u postgres psql -c "\l" | grep cloverweb

# 站点
curl -I http://communitygarden.org.cn  # 此时 502/404 都行，证明 Nginx 在跑
```

---

## 3. 第 2 步：把项目推送到 GitHub 并配置 Secrets

### 3.1 在 GitHub 上创建仓库（如已有跳过）

在 https://github.com/new 创建：
- 名称：`cloverweb`（或你想要的）
- 可见性：Private
- **不要**勾选 Add README / .gitignore / license（本地已有）

### 3.2 本地推送代码

```bash
# 在项目根目录
cd "/Users/fanfan/Library/Mobile Documents/com~apple~CloudDocs/CloverHub+web管理"

# 确认远程仓库地址
git remote -v
# 如果还没有
git remote add origin git@github.com:fanhaoyangs/cloverweb.git

# 推送 main 分支
git push -u origin main
```

### 3.3 配置 GitHub Secrets

仓库页面 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

逐个添加以下 4 个：

| Name | Value | 备注 |
|---|---|---|
| `SSH_HOST` | CVM 公网 IP | 例如 `1.2.3.4` |
| `SSH_USER` | `cloverweb-deploy` | 部署用户名（不是 root） |
| `SSH_PORT` | `22` | 可选，默认 22 |
| `SSH_PRIVATE_KEY` | 私钥**完整内容** | 见 3.4 |

### 3.4 生成并配置部署密钥

**3.4.1 本地生成专用密钥对（不要用你个人 SSH 登录 CVM 的那个）**

```bash
# 本地（macOS / Linux）
ssh-keygen -t ed25519 -C "cloverweb-deploy-ci" -f ~/.ssh/cloverweb_deploy_key
# 不要设密码（GitHub Actions 不会交互输入）
```

会生成两个文件：
- 私钥：`~/.ssh/cloverweb_deploy_key` → **填到 GitHub Secret `SSH_PRIVATE_KEY`**
- 公钥：`~/.ssh/cloverweb_deploy_key.pub` → **追加到 CVM**

**3.4.2 私钥填到 GitHub**

```bash
cat ~/.ssh/cloverweb_deploy_key
# 把输出整段（含 BEGIN/END 标记）粘贴到 GitHub Secret SSH_PRIVATE_KEY 的 Value
```

**3.4.3 公钥追加到 CVM 的部署用户**

```bash
# 本地
cat ~/.ssh/cloverweb_deploy_key.pub

# CVM 上
ssh root@<CVM_IP>
mkdir -p /home/cloverweb-deploy/.ssh
# 粘贴公钥（一行）
echo "ssh-ed25519 AAAA... cloverweb-deploy-ci" >> /home/cloverweb-deploy/.ssh/authorized_keys
chown -R cloverweb-deploy:cloverweb-deploy /home/cloverweb-deploy/.ssh
chmod 700 /home/cloverweb-deploy/.ssh
chmod 600 /home/cloverweb-deploy/.ssh/authorized_keys
```

**3.4.4 本地验证 sudo 白名单**

```bash
# 本地以部署用户身份 SSH 进 CVM（先用 root 把该用户写进 .ssh，或临时用 root 配公钥）
ssh -i ~/.ssh/cloverweb_deploy_key cloverweb-deploy@<CVM_IP> "sudo -n bash /opt/cloverweb/deploy/deploy.sh /tmp/dummy.tar.gz"
# 应该返回 sudo: a password is required 的提示或直接执行（取决于 tar 是否存在）
# 关键是 sudo 不会要求输入密码
```

---

## 4. 第 3 步：补全 CVM 上的 `.env` 凭证 + 创建 superuser

### 4.1 补全 `.env`

`setup-server.sh` 已经生成了 `/opt/cloverweb/backend/.env`，但 COS / 飞书凭证留空，需要手动补：

```bash
ssh root@<CVM_IP>
sudo -u cloverweb vi /opt/cloverweb/backend/.env
```

填入 4 个 COS 字段：

```ini
COS_SECRET_ID=AKIDxxxxxxxxxxxxxxxxxxxx
COS_SECRET_KEY=xxxxxxxxxxxxxxxxxxxxxxxx
COS_BUCKET=images-community-1300000000
COS_BASE_URL=https://images.communitygarden.org.cn
# COS_REGION 已是默认 ap-shanghai，如你的桶在其他区，修改这一行
```

如果暂时不用飞书登录，**可以不填** `FEISHU_*`（用账号密码登录即可）。

保存后确保权限：
```bash
sudo chown cloverweb:cloverweb /opt/cloverweb/backend/.env
sudo chmod 600 /opt/cloverweb/backend/.env
```

### 4.2 创建 CMS superuser

第一次部署后会自动跑 `migrate`，但 superuser 需要手动创建。**有两种方式**：

**方式 A：在 CI 跑完首次部署后，SSH 进 CVM 创建**

```bash
ssh root@<CVM_IP>
sudo -u cloverweb /opt/cloverweb/backend/venv/bin/python /opt/cloverweb/backend/manage.py createsuperuser
# 按提示输入 Username、Email、Password
# 建议用：admin / 一个强密码
```

**方式 B：先把代码临时放一份到 CVM 手动跑（首次部署前用）**

```bash
# 在 CVM 上克隆仓库
ssh root@<CVM_IP>
cd /opt
git clone git@github.com:fanhaoyangs/cloverweb.git cloverweb-tmp
cd cloverweb-tmp/backend
python3 -m venv venv
venv/bin/pip install -r requirements.txt
# 复制 .env（已经存在）但要加 DJANGO_SETTINGS_MODULE
echo "DJANGO_SETTINGS_MODULE=cloverweb.settings.prod" >> .env
# 跑 migrate 建表
sudo -u cloverweb bash -c "set -a && source .env && set +a && venv/bin/python manage.py migrate"
sudo -u cloverweb bash -c "set -a && source .env && set +a && venv/bin/python manage.py createsuperuser"
# 清掉临时目录
rm -rf /opt/cloverweb-tmp
```

> 推荐方式 A，干净不易错。

---

## 5. 第 4 步：触发首次部署并验证

### 5.1 触发部署

在 GitHub 仓库 → **Actions** → 左侧选 **Deploy to CVM** → 右侧 **Run workflow** → 选 main 分支 → 绿色按钮

也可以直接 `git push`（push main 会自动触发），但首次建议手动触发方便看日志。

### 5.2 看 CI 日志

约 3-8 分钟，关注这几步：
- **Build frontend**：应当 2-3 分钟
- **Pack deploy bundle**：几秒
- **Upload & deploy**：1-3 分钟
- **Health check**：

```
Active: active
API HTTP 200
```

如果失败看下面 [常见问题](#7-常见问题)。

### 5.3 验证线上站点

```bash
# HTTPS 访问
curl -I https://communitygarden.org.cn/                    # 200/301
curl -I https://communitygarden.org.cn/admin/login         # 200
curl -I https://communitygarden.org.cn/api/ueditor/?action=config   # 200

# 浏览器访问 https://communitygarden.org.cn/admin/login
# 用 superuser 账号密码登录
# 创建一篇带图片的文章 → 在文章编辑页 UEditor 上传图 → 应上传到 COS 并返回 URL
```

### 5.4 证书自动续签

certbot 装的时候会自动加一个 systemd timer，60 天左右自动续期。可以验证：

```bash
ssh root@<CVM_IP>
sudo systemctl list-timers | grep certbot
# 应该看到 certbot.timer 下次运行时间
```

---

## 6. 日常运维速查

### 6.1 查看服务状态

```bash
ssh root@<CVM_IP>

systemctl status cloverweb        # gunicorn 状态
systemctl status nginx            # nginx
systemctl status postgresql       # PG
journalctl -u cloverweb -n 100    # 实时日志
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### 6.2 重启服务

```bash
sudo systemctl restart cloverweb   # 重新跑 gunicorn（migrate 不重跑）
sudo systemctl reload nginx        # 平滑重载配置
```

### 6.3 手动触发部署

GitHub 仓库 → Actions → Deploy to CVM → Run workflow。

或本地：
```bash
# 提交空 commit 也能触发
git commit --allow-empty -m "ci: 重新部署" && git push
```

### 6.4 手动跑部署脚本（紧急回滚/本地调试用）

```bash
ssh cloverweb-deploy@<CVM_IP>
# 需要先 scp 一份 tarball
sudo bash /opt/cloverweb/deploy/deploy.sh /tmp/cloverweb-deploy.tar.gz
```

### 6.5 备份数据库

```bash
# 本地
ssh root@<CVM_IP> "sudo -u postgres pg_dump -Fc cloverweb" > backups/cloverweb-$(date +%Y%m%d).dump

# 恢复
scp backups/cloverweb-20260818.dump root@<CVM_IP>:/tmp/
ssh root@<CVM_IP> "sudo -u postgres pg_restore -d cloverweb --clean /tmp/cloverweb-20260818.dump"
```

### 6.6 升级依赖

```bash
# 本地修改 backend/requirements.txt 后
git add backend/requirements.txt
git commit -m "chore: 升级依赖"
git push   # 自动触发 CI
```

### 6.7 更换 .env（凭证轮换）

```bash
ssh root@<CVM_IP>
sudo -u cloverweb vi /opt/cloverweb/backend/.env
# 不需要重启，gunicorn 在 deploy.sh 末尾会自动 restart
# 或手动
sudo systemctl restart cloverweb
```

---

## 7. 常见问题

### 7.1 CI 部署失败：Permission denied (publickey)

**原因**：GitHub Secret `SSH_PRIVATE_KEY` 配错，或 CVM 端公钥没追加。

**排查**：
```bash
# 1. 本地手动用这个私钥 SSH 一次
ssh -i ~/.ssh/cloverweb_deploy_key -o IdentitiesOnly=yes cloverweb-deploy@<CVM_IP> "echo ok"
# 2. 确认 CVM 端公钥
ssh root@<CVM_IP> "cat /home/cloverweb-deploy/.ssh/authorized_keys"
```

### 7.2 CI 部署失败：sudo: a password is required

**原因**：`/etc/sudoers.d/cloverweb-deploy` 缺失或权限错。

**修复**：
```bash
ssh root@<CVM_IP>
sudo cat /etc/sudoers.d/cloverweb-deploy
# 应该看到：cloverweb-deploy ALL=(root) NOPASSWD: /bin/bash /opt/cloverweb/deploy/deploy.sh *
# 没有就重新跑 setup-server.sh 步骤 4
```

### 7.3 Health check 失败：API HTTP 502/503

**原因**：gunicorn 启动失败（多半是 .env 缺凭证 / DB 连不上 / migrate 没跑）。

**排查**：
```bash
ssh root@<CVM_IP>
sudo journalctl -u cloverweb -n 50
# 看报错。常见：
# 1. DJANGO_SECRET_KEY missing → 改 prod.py 或在 .env 加
# 2. psycopg2.OperationalError: connection to server → 查 PG 是否启动、密码是否对
# 3. relation "xxx" does not exist → migrate 没跑，手动执行：
sudo -u cloverweb bash -c "cd /opt/cloverweb/backend && set -a && source .env && set +a && venv/bin/python manage.py migrate"
```

### 7.4 首页 404 但 API 正常

**原因**：Nginx 的 `try_files` 没生效（history 路由）。

**排查**：
```bash
ssh root@<CVM_IP>
cat /etc/nginx/sites-enabled/cloverweb | grep try_files
# 必须有：try_files $uri $uri/ /index.html;
sudo nginx -t && sudo systemctl reload nginx
```

### 7.5 上传图片 500

**排查**：
```bash
ssh root@<CVM_IP>
sudo -u cloverweb bash -c "cd /opt/cloverweb/backend && set -a && source .env && set +a && venv/bin/python -c 'from apps.common import cos; print(cos.get_cos_client())'"
# 如果报 CosNotConfigured → 检查 .env COS 四个字段
# 如果报 SignatureDoesNotMatch → SecretId/Key 错了，重新生成
```

### 7.6 证书过期 / 失败

```bash
ssh root@<CVM_IP>
sudo certbot renew --dry-run   # 测试
sudo certbot renew             # 实际续签
sudo systemctl reload nginx
```

### 7.7 502 + "Connection refused [::1]:8000"

**原因**：gunicorn bind 用了 IPv6 0.0.0.0，而 Nginx 用 127.0.0.1 访问。

**修复**（已修过，如果还遇到）：
`/opt/cloverweb/deploy/systemd/cloverweb.service` 里 bind 改为 `--bind 127.0.0.1:8000`，然后 `sudo systemctl daemon-reload && sudo systemctl restart cloverweb`。

### 7.8 内存吃紧 OOM Killed

**症状**：`journalctl -u cloverweb` 看到 `oom-kill`。

**修复**（已设 MemoryMax 768M；如果还杀进程）：
- 把 nginx worker 数降低：`/etc/nginx/nginx.conf` 中 `worker_processes auto;` 改为 `worker_processes 1;`
- 检查 `ps aux --sort=-%mem | head` 看谁在吃内存
- 加 swap：
  ```bash
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile && sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
  ```

### 7.9 想看 CI 部署的 tar 里到底有什么

GitHub Actions → 选运行的 run → 左侧 **Pack deploy bundle** 步骤会显示文件列表。或者本地：
```bash
cd "/Users/fanfan/Library/Mobile Documents/com~apple~CloudDocs/CloverHub+web管理"
mkdir -p /tmp/check-bundle
rsync -a backend/ /tmp/check-bundle/backend/ \
  --exclude venv/ --exclude __pycache__/ --exclude db.sqlite3 \
  --exclude '.env*' --exclude staticfiles/ --exclude media/
cp -r web/dist /tmp/check-bundle/web
cd /tmp/check-bundle && tar -czf /tmp/check.tar.gz .
tar -tzf /tmp/check.tar.gz | head -30
# 确认 .env 没被打包（用 grep 验证）
tar -tzf /tmp/check.tar.gz | grep -E '\.env|venv'  # 应为空
rm -rf /tmp/check-bundle /tmp/check.tar.gz
```

---

## 8. 紧急情况：完全重置 CVM

如果一切都乱了，需要重新初始化：

```bash
ssh root@<CVM_IP>

# 1. 停止并清理服务
sudo systemctl stop cloverweb
sudo systemctl disable cloverweb
sudo rm -f /etc/systemd/system/cloverweb.service
sudo rm -f /etc/nginx/sites-enabled/cloverweb /etc/nginx/sites-available/cloverweb
sudo systemctl daemon-reload
sudo systemctl reload nginx

# 2. 删数据库（会丢所有数据！）
sudo -u postgres psql -c "DROP DATABASE IF EXISTS cloverweb;"
sudo -u postgres psql -c "DROP USER IF EXISTS cloverweb;"

# 3. 删应用代码
sudo rm -rf /opt/cloverweb
sudo userdel -r cloverweb 2>/dev/null
sudo userdel -r cloverweb-deploy 2>/dev/null
sudo rm -f /etc/sudoers.d/cloverweb-deploy

# 4. 重新跑 setup-server.sh
# （重新上传 deploy/ 目录后再跑）
```

> ⚠️ 这一步会清空所有文章和上传记录，先在 `6.5 备份数据库` 做了再删。

---

## 9. 检查清单

首次部署前对照打勾：

- [ ] CVM 已建好，2C2G，公网 IP 已知
- [ ] 域名 `communitygarden.org.cn` 解析到 CVM IP
- [ ] 腾讯云 COS 桶已建（公有读私有写，已开 CORS）
- [ ] COS SecretId/Key 已保存
- [ ] GitHub 仓库已建（如 `fanhaoyangs/cloverweb`）
- [ ] 本地已生成专用 ed25519 密钥对
- [ ] CVM 已跑 `setup-server.sh` 成功
- [ ] GitHub Secrets 4 个已配齐（SSH_HOST/SSH_USER/SSH_PORT/SSH_PRIVATE_KEY）
- [ ] CVM `/home/cloverweb-deploy/.ssh/authorized_keys` 追加了公钥
- [ ] CVM `/opt/cloverweb/backend/.env` 补了 COS 凭证
- [ ] 首次 CI 部署完成，superuser 已创建
- [ ] 浏览器打开 https://communitygarden.org.cn 看到首页
- [ ] 浏览器打开 https://communitygarden.org.cn/admin/login 能登录
- [ ] CMS 发一篇带图的文章，图片上传到 COS 成功

全部打勾 = 上线完成。
