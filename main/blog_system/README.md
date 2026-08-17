# 资讯分享博客系统

四叶草堂官网资讯分享系统，基于Flask + Vditor + SQLite + 腾讯云COS构建。

## 功能特性

- 📝 文章管理：创建、编辑、发布、归档文章
- 🏷️ 分类管理：灵活的文章分类
- 📷 图床支持：腾讯云COS对象存储图片
- ✍️ 所见即所得编辑器：Vditor Markdown编辑器
- 🎨 完美风格统一：与现有网站视觉风格一致
- 📱 响应式设计：支持移动端访问
- 🔒 安全防护：CSRF保护、XSS过滤、密码加密

## 技术栈

- **后端**: Flask 2.3 + Python 3.8+
- **数据库**: SQLite 3
- **编辑器**: Vditor (所见即所得Markdown)
- **图片存储**: 腾讯云COS对象存储
- **部署**: Gunicorn + Nginx + systemd

## 目录结构

```
blog_system/
├── app.py              # Flask主应用
├── config.py           # 配置文件
├── models.py           # 数据库模型
├── cos_utils.py        # COS上传工具
├── requirements.txt    # Python依赖
├── gunicorn.conf.py    # Gunicorn配置
├── static/             # 静态资源
│   ├── css/
│   ├── js/
│   └── images/
├── templates/          # HTML模板
│   ├── base.html
│   ├── news.html
│   ├── article.html
│   ├── admin/          # 后台模板
│   └── errors/         # 错误页面
├── data/               # 数据目录
│   └── posts.db        # SQLite数据库
└── deploy/             # 部署配置
    ├── nginx.conf
    └── blog-system.service
```

## 快速开始

### 1. 安装依赖

```bash
cd blog_system
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### 2. 配置环境

```bash
cp .env.example .env
# 编辑 .env 文件，填入实际配置值
```

### 3. 初始化数据库

```bash
flask init-db
```

这将：
- 创建数据库表
- 创建默认管理员账号（admin/admin123）
- 创建默认分类

### 4. 本地运行

```bash
python app.py
```

访问 http://localhost:5000/news

### 5. 后台管理

访问 http://localhost:5000/admin/login

默认账号：`admin`
默认密码：`admin123`

## 腾讯云COS配置

### 1. 创建COS存储桶

1. 登录[腾讯云控制台](https://console.cloud.tencent.com/)
2. 进入对象存储COS
3. 创建存储桶（地域选择与服务器相同）
4. 设置为"公有读私有写"

### 2. 配置CORS

在存储桶设置中添加CORS规则：
- 来源：`*` 或您的域名
- 方法：GET, POST, PUT, DELETE
- 响应头：Content-Type

### 3. 配置子域名

1. 在域名服务商控制台添加CNAME记录
2. 记录值指向COS存储桶的访问域名
3. 在COS控制台为子域名配置SSL证书

## 生产部署

### 1. 服务器准备

```bash
# 安装Python和pip
sudo apt update
sudo apt install python3 python3-pip python3-venv

# 安装Nginx
sudo apt install nginx
```

### 2. 上传代码

```bash
scp -r blog_system user@server:/var/www/
```

### 3. 配置环境

```bash
cd /var/www/blog_system
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 文件
```

### 4. 初始化数据库

```bash
flask init-db
```

### 5. 配置systemd服务

```bash
sudo cp deploy/blog-system.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable blog-system
sudo systemctl start blog-system
```

### 6. 配置Nginx

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/blog-system
sudo ln -s /etc/nginx/sites-available/blog-system /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 7. 配置SSL证书（使用Let's Encrypt）

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d communitygarden.org.cn -d images.communitygarden.org.cn
```

## 使用说明

### 文章编辑

- 支持Markdown语法
- 可视化工具栏辅助排版
- 图片拖拽或粘贴上传
- 实时保存预览

### 分类管理

- 创建分类用于文章归类
- 支持排序权重设置
- 分类别名用于URL显示

### 图片管理

- 封面图上传
- 文章内嵌图片上传
- 自动存储到COS云端

## 账号安全

首次部署后请立即修改默认密码！

```python
# 在Python环境中修改密码
from app import app, db, User

with app.app_context():
    user = User.query.filter_by(username='admin').first()
    user.set_password('your-new-password')
    db.session.commit()
```

## 备份与恢复

### 备份数据库

```bash
cp data/posts.db posts_backup_$(date +%Y%m%d).db
```

### 恢复数据库

```bash
cp posts_backup_*.db data/posts.db
```

## 常见问题

### Q: 图片上传失败
A: 检查COS配置是否正确，确保CORS规则已设置。

### Q: 后台无法登录
A: 检查用户名密码，初始账号为 admin/admin123。

### Q: 文章显示404
A: 确保文章已发布，检查slug是否正确。

## 许可证

MIT License
