# CloverHub 官网重构方案（v3.2 · 2026-08-17）

> 决策摘要（v3.2）：
> - **命名**：网站产品名统一 `cloverweb`（cloverhub 是小程序名）；Django 项目 `cloverweb`，CVM 用户/目录 `cloverweb`，服务 `cloverweb-web.service`，PG 库/用户 `cloverweb`，部署根 `/home/cloverweb/`。GitHub 仓库名 `clover-web-admin` 暂不改名
> - **目标架构**：单站单栈。`main/` 整体迁出后归档，不再保留
> - **静态 HTML**：3 个旧静态页（index/clover/philosophy）直接迁到 Vue 组件
> - **数据迁移**：**不做**。SQLite 库数据少；CloudBase `articles` 只有封面+标题（无正文）
> - **飞书 OAuth**：保留，**仅**作为 CMS 内部登录
> - **工时系统**：**不迁**（用户已备份，单独部署到其他地方）
> - **Vditor**：**不用**（旧代码），新系统统一 UEditorPlus
>
> **v3.1 修正**（基于实际代码审查）：
> - **A1**：飞书 OAuth 端点改用国内版（沿用旧系统 `feishu_auth.py` 的 `open-apis/...`）
> - **A2**：`git mv` 改普通 `mv`（根目录非 git 仓库）；补 git 初始化步骤
> - **A3**：删除 manualChunks 里 `ueditor-vendor` 那条（public/ 不进 rollup）
> - **B1**：路由改 `createWebHistory`（hash 路由无 SEO）
> - **B2**：CI 改为本地构建后 scp artifact 到 CVM（避免 2C2G 上 build OOM）
> - **B3**：飞书回调 token 改一次性 code 中转 + 前端换 JWT（防 URL 泄露）

---

## 〇、目标与现状

### 0.1 现状盘点（v3）

| 目录 | 实质 | v3 处置 | 状态 |
|---|---|---|---|
| `main/index.html` / `clover.html` / `philosophy.html` | 旧版静态官网 | **迁到 Vue 组件**（Home/About/Philosophy） | Phase 2.2 |
| `main/blog_system/`（Flask + SQLite + 飞书 OAuth + 工时系统） | 旧版博客 + 内部工具 | **整体归档**（不共存，不迁数据） | Phase 2.7 |
| `main/ppt_project/` | PPT 设计稿 | **归档** | Phase 2.7 |
| `main/docs/` | 项目文档 | **归档** | Phase 2.7 |
| `wechat-mini-program/`（整目录） | 微信小程序 | **删除** | ✅ Phase 1 |
| `web-admin/src/views/{HomePage,AboutPage,PhilosophyPage,NewsList,ArticleDetail}.vue` | 现代官网公共页 | **保留 + 内容替换** | Phase 2.2 |
| `web-admin/src/views/{ActivityList,ActivityEdit,ActivityDetail,ArticleList,ArticleEdit,UserList,UserDetail,UserData,Backup,Login,Home(活动中心)}.vue` | 小程序后台 + 活动链 | **删除** | ✅ Phase 1 |
| `web-admin/src/components/{UEditor,content-editor/}` | UEditorPlus 封装 | **保留** | ✅ |
| `web-admin/src/components/{PublicLayout,SiteHeader,SiteFooter}` | 公共布局 | 保留 | ✅ |
| `web-admin/src/middlewares/ueditor.js` | dev 期 UEditor mock | 保留 | ✅ |
| `web-admin/src/api/article.js` | 文章 API | 改写为只读版（Phase 2.2 改 axios） | ✅ |
| `web-admin/api/ueditor/upload.js` | UEditor 上传（生产） | 保留 | ✅ |
| `web-admin/public/UEditorPlus/` | 编辑器静态资源 | **保留** | ✅ |
| `web-admin/.github/workflows/deploy.yml` | CloudBase 部署 | **删除** | ✅ |
| `web-admin/cloudbaserc.json` | CloudBase 配置 | **删除** | ✅ |
| `web-admin/dist*`（构建产物 + 压缩包） | 一次性产物 | **删除** | ✅ |
| `web-admin/.env`、`web-admin/.agents/`、`web-admin/.trae/` | 配置与计划 | 保留 | 后续清理 |
| `CODE_WIKI.md` | 旧维基 | **删除** | ✅ |
| `.trae/documents/main-to-cloudbase-migration-plan.md` | 过期方案 | **删除** | ✅ |
| `.trae/documents/cloverweb-architecture-doc-plan.md` | 未采用 | **删除** | ✅ |
| `.trae/documents/2026-competition-plan.md` | 网站侧竞赛 plan | 保留 | ✅ |
| `.trae/documents/cloverhub-refactor-plan.md` | 本文件 | 保留 | ✅ |

### 0.2 目标架构（v3）

```
/Users/fanfan/Library/Mobile Documents/com~apple~CloudDocs/CloverHub+web管理/
├── main/                           # 旧站，Phase 2.7 后整体归档（tar.gz 后删）
├── web/                            # ⭐ 官网前端（来源 web-admin 公共部分 + 迁入静态页内容）
│   ├── src/views/
│   │   ├── Home.vue                # ⭐ 替换：原 HomePage + 迁入 main/index.html 内容
│   │   ├── About.vue               # ⭐ 替换：原 AboutPage + 迁入 main/clover.html 内容
│   │   ├── Philosophy.vue          # ⭐ 替换：原 PhilosophyPage + 迁入 main/philosophy.html 内容
│   │   ├── News.vue                # 资讯列表
│   │   ├── Article.vue             # 资讯详情
│   │   ├── bbs/                    # Phase 3 新增
│   │   │   ├── Index.vue
│   │   │   ├── Topic.vue
│   │   │   └── NewTopic.vue
│   │   ├── contest/                # Phase 4 新增
│   │   │   ├── Home.vue
│   │   │   ├── Register.vue
│   │   │   └── Rank.vue
│   │   └── admin/                  # Phase 2.2 新增（CMS 后台）
│   │       ├── ArticleList.vue
│   │       ├── ArticleEdit.vue
│   │       ├── Media.vue
│   │       └── DjangoAdminEmbed.vue
│   ├── src/components/
│   │   ├── PublicLayout.vue
│   │   ├── SiteHeader.vue
│   │   ├── SiteFooter.vue
│   │   ├── content-editor/         # ⭐ UEditorPlus 封装
│   │   │   ├── ContentEditor.vue
│   │   │   └── UEditor.vue
│   │   └── CmsLayout.vue           # Phase 2.2 新增（CMS 后台布局）
│   ├── src/router/index.js
│   ├── src/api/                    # axios 封装
│   ├── src/utils/cos-upload.js
│   ├── src/styles/common.css
│   ├── src/App.vue
│   ├── src/main.js
│   ├── public/UEditorPlus/         # 编辑器静态资源
│   ├── package.json
│   └── vite.config.js
├── backend/                        # ⭐ 新建：Django 5 后端
│   ├── apps/
│   │   ├── content/                # 文章/资讯
│   │   ├── team/                   # 团队介绍
│   │   ├── auth_custom/            # 自定义用户 + 飞书 OAuth + JWT
│   │   ├── bbs/                    # 论坛（Phase 3）
│   │   ├── contest/                # 社区花园竞赛（Phase 4）
│   │   └── common/                 # 共享工具（COS、UEditor 接口、邮件）
│   ├── settings/{base,dev,prod}.py
│   ├── requirements.txt
│   ├── manage.py
│   └── scripts/
│       └── seed_initial_data.py    # 初始化种子数据（手动创建关键文章）
├── deploy/
│   ├── nginx.conf
│   ├── cloverweb-web.service
│   └── backup.sh
├── archive/                        # ⭐ Phase 2.7 新建：旧 main 归档
│   ├── main-2026-08-xx.tar.gz
│   └── ARCHIVE.md                  # 归档说明
├── .github/workflows/deploy.yml    # CVM 部署
├── README.md
├── ARCHITECTURE.md
└── .trae/documents/
    └── cloverhub-refactor-plan.md  # 本文件
```

### 0.3 关键决策记录（v3）

| 决策 | 选项 | **v3 选定** | 理由 |
|---|---|---|---|
| 后端框架 | Django / FastAPI | **Django 5** | 与 blog_system 同 Python 生态；自带 admin/ORM/auth |
| 数据库 | SQLite / PostgreSQL | **PostgreSQL 16** | UGC 内容增长后关系查询/全文搜索更稳 |
| 前端 | 保留 Vue 3（JS） | **Vue 3 + Vite（JS）** | 现有 web-admin 已稳定，零重写工作量 |
| 编辑器 | UEditorPlus / 其他 | **UEditorPlus**（Vditor 不用） | 你已明确要求延续使用；支持图片/视频/公式 |
| CMS 后台 | Django admin / 自建 | **Django admin 套 UEditorPlus iframe** | 借用 Django admin 的 RBAC + 表单 + 列表 |
| 文件存储 | CloudBase 云存储 / 腾讯云 COS | **腾讯云 COS（直连）** | web-admin 已用 `images.communitygarden.org.cn` |
| 鉴权（CMS） | 飞书 OAuth / 邮箱密码 | **飞书 OAuth**（你已确认） | 内部员工统一用飞书；无新用户注册入口 |
| 鉴权（BBS） | 飞书 OAuth / 邮箱 | **邮箱注册 + 飞书 OAuth 可选** | BBS 是公开用户 |
| 部署 | Docker / 裸 systemd | **裸 systemd + Gunicorn + Nginx** | 2C2G 不上 Docker |
| 媒体上传 | 前端直传 COS / 后端中转 | **前端直传 COS（预签名 URL）** | 减后端压力 |
| 静态页迁移方式 | A. 迁 Vue 组件 / B. iframe / C. 废弃 | **A. 迁 Vue 组件**（你已确认） | 单一前端栈，SEO 友好 |
| CloudBase articles 数据迁移 | 迁 / 不迁 | **不迁** | 仅有封面+标题，无正文，新站从零 |
| SQLite blog_system 数据迁移 | 迁 / 不迁 | **不迁** | 数据很少 |
| 工时系统 | 迁 / 不迁 | **不迁**（用户单独部署） | 与主体网站无关 |
| main/ 共存 | 保留端口 8001 / 整体归档 | **整体归档** | 静态页已迁 Vue，blog_system 不再需要 |
| CloudBase 旧环境保留 | 1 月 / 3 月 | **2 周**（观察期） | 资源免费 |

---

## 一、Phase 1：立即移除 ✅ 已完成

（v3 不变，见 v1/v2 详细清单）
- ✅ `wechat-mini-program/` 删除
- ✅ `web-admin/` 后台代码清理
- ✅ `.trae/` 过期文档清理
- ✅ `CODE_WIKI.md` 删除
- ✅ UEditorPlus 完整保留
- ✅ `web-admin` build 通过
- ✅ `main/` 暂留

---

## 二、Phase 2：网站全栈重构到 CVM（Week 3-8）

> 目标：单栈单后端。完成后 `https://communitygarden.org.cn` 跑在新 CVM，旧 main/ 归档。

### 2.1 后端：新建 Django 项目 `backend/`

#### 2.1.1 初始化

```bash
mkdir backend && cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install \
  django==5.0.* \
  djangorestframework \
  djangorestframework-simplejwt \
  psycopg2-binary \
  django-cors-headers \
  gunicorn \
  pillow \
  cos-python-sdk-v5 \
  requests \
  python-dotenv

django-admin startproject cloverweb .
python manage.py startapp content
python manage.py startapp team
python manage.py startapp auth_custom
python manage.py startapp bbs
python manage.py startapp contest
python manage.py startapp common
```

`requirements.txt`：
```
Django==5.0.*
djangorestframework==3.15.*
djangorestframework-simplejwt==5.3.*
psycopg2-binary==2.9.*
django-cors-headers==4.4.*
gunicorn==22.*
Pillow==10.*
cos-python-sdk-v5==1.9.*
requests==2.32.*
python-dotenv==1.0.*
```

#### 2.1.2 数据模型（v3）

**`apps/auth_custom/models.py`**：
```python
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """自定义用户：飞书 OAuth 登录 + JWT 鉴权"""
    feishu_open_id = models.CharField(max_length=100, blank=True, db_index=True)
    feishu_union_id = models.CharField(max_length=100, blank=True)
    avatar_url = models.URLField(blank=True)
    display_name = models.CharField(max_length=100, blank=True)
    is_feishu_user = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'auth_user_ext'
```

**`apps/content/models.py`**：
```python
class Category(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=50)
    order = models.IntegerField(default=0)
    class Meta:
        db_table = 'content_category'
        ordering = ['order', 'id']

class Tag(models.Model):
    name = models.CharField(max_length=30, unique=True)
    class Meta:
        db_table = 'content_tag'

class Article(models.Model):
    STATUS = [('draft','草稿'),('published','已发布'),('archived','已归档')]
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    excerpt = models.TextField(blank=True)
    content_html = models.TextField()  # UEditorPlus 输出
    cover_image = models.URLField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='articles')
    tags = models.ManyToManyField(Tag, blank=True)
    website_sections = models.JSONField(default=list)  # ['home_carousel','news_top']
    section_order = models.IntegerField(default=0)
    author = models.ForeignKey('auth_custom.User', on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=STATUS, default='draft')
    view_count = models.IntegerField(default=0)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'content_article'
        indexes = [
            models.Index(fields=['status', '-published_at']),
            models.Index(fields=['category', '-published_at']),
        ]
        ordering = ['-published_at']
```

**`apps/team/models.py`**：
```python
class TeamMember(models.Model):
    name = models.CharField(max_length=50)
    title = models.CharField(max_length=100)
    bio = models.TextField(blank=True)
    avatar = models.URLField(blank=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    joined_at = models.DateField(null=True, blank=True)
    class Meta:
        ordering = ['order', 'name']

class SitePage(models.Model):
    """静态页面内容（关于我们 / 理念 等）"""
    slug = models.SlugField(unique=True)  # 'about', 'philosophy'
    title = models.CharField(max_length=100)
    content_html = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'team_sitepage'
```

> **v3 关键点**：新增 `SitePage` 模型，专门承载从 `main/index.html` / `clover.html` / `philosophy.html` 迁入的静态内容。Vue 端 `Home.vue` / `About.vue` / `Philosophy.vue` 调 `/api/sitepage/<slug>/` 拿 HTML 内容渲染。

**`apps/bbs/models.py`**（Phase 3）：
```python
class Topic(models.Model):
    CATEGORY_CHOICES = [
        ('announce','公告'),('discuss','讨论'),('feedback','反馈'),
        ('find_team','求组队'),('share','分享'),('other','其他')
    ]
    title = models.CharField(max_length=200)
    author = models.ForeignKey('auth_custom.User', on_delete=models.CASCADE, related_name='topics')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='discuss')
    tags = models.JSONField(default=list)
    content_html = models.TextField()
    view_count = models.IntegerField(default=0)
    reply_count = models.IntegerField(default=0)
    like_count = models.IntegerField(default=0)
    last_reply_at = models.DateTimeField(null=True, blank=True)
    is_pinned = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-is_pinned', '-last_reply_at']

class Post(models.Model):
    topic = models.ForeignKey(Topic, related_name='posts', on_delete=models.CASCADE)
    floor = models.IntegerField()
    author = models.ForeignKey('auth_custom.User', on_delete=models.CASCADE, related_name='posts')
    content_html = models.TextField()
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    like_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('topic', 'floor')
        ordering = ['floor']

class Like(models.Model):
    user = models.ForeignKey('auth_custom.User', on_delete=models.CASCADE)
    target_type = models.CharField(max_length=10)
    target_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('user', 'target_type', 'target_id')
```

**`apps/contest/models.py`**（Phase 4）：
```python
class Season(models.Model):
    STATUS = [('upcoming','即将开始'),('registration','报名中'),('judging','评审中'),('closed','已结束')]
    year = models.IntegerField(unique=True)
    title = models.CharField(max_length=100)
    description_html = models.TextField()
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    registration_deadline = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS)
    rules_pdf_url = models.URLField(blank=True)

class Team(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='teams')
    name = models.CharField(max_length=100)
    captain = models.ForeignKey('auth_custom.User', on_delete=models.PROTECT, related_name='captained_teams')
    members = models.ManyToManyField('auth_custom.User', related_name='teams')
    city = models.CharField(max_length=50)
    school = models.CharField(max_length=100, blank=True)
    contact_phone = models.CharField(max_length=20)
    registered_at = models.DateTimeField(auto_now_add=True)

class Submission(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='submissions')
    title = models.CharField(max_length=200)
    description_html = models.TextField()
    files = models.JSONField(default=list)
    submitted_at = models.DateTimeField()

class Score(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='scores')
    judge = models.ForeignKey('auth_custom.User', on_delete=models.CASCADE, related_name='scores')
    score_design = models.DecimalField(max_digits=4, decimal_places=1)
    score_engagement = models.DecimalField(max_digits=4, decimal_places=1)
    score_innovation = models.DecimalField(max_digits=4, decimal_places=1)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('submission', 'judge')

class Ranking(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='rankings')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='rankings')
    total_score = models.DecimalField(max_digits=6, decimal_places=2)
    rank = models.IntegerField()
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        unique_together = ('season', 'team')
        ordering = ['season', 'rank']
```

**`apps/common/models.py`**：
```python
class SiteConfig(models.Model):
    """全局站点配置（key-value 单行表）"""
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.CharField(max_length=200, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

class UploadedFile(models.Model):
    """UEditor 上传的文件记录"""
    FILE_TYPE = [('image','图片'),('video','视频'),('file','文件')]
    file_type = models.CharField(max_length=10, choices=FILE_TYPE)
    original_name = models.CharField(max_length=200)
    cos_key = models.CharField(max_length=500)
    cos_url = models.URLField()
    file_size = models.IntegerField()
    mime_type = models.CharField(max_length=100)
    uploader = models.ForeignKey('auth_custom.User', on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
```

#### 2.1.3 REST API（DRF）

**Content API（公开）**：
| Endpoint | Method | 用途 |
|---|---|---|
| `/api/articles/` | GET | 文章列表（分页/分类/标签/关键词） |
| `/api/articles/<slug>/` | GET | 文章详情 + view_count++ |
| `/api/articles/featured/` | GET | 首页 section 卡片 |
| `/api/categories/` | GET | 分类列表 |
| `/api/tags/` | GET | 标签列表 |
| `/api/sitepage/<slug>/` | GET | **v3 新增**：静态页内容（Home/About/Philosophy） |

**Content API（管理，需飞书登录）**：
| Endpoint | Method | 用途 |
|---|---|---|
| `/api/admin/articles/` | GET / POST | 文章 CRUD |
| `/api/admin/articles/<id>/` | PUT / PATCH / DELETE | 文章 CRUD |
| `/api/admin/articles/<id>/publish/` | POST | 发布 |
| `/api/admin/sitepages/` | GET / POST | 静态页管理 |
| `/api/admin/sitepages/<slug>/` | PUT | 静态页更新 |

**Auth API**：
| Endpoint | Method | 用途 |
|---|---|---|
| `/api/auth/feishu/login/` | GET | 飞书 OAuth 跳转 |
| `/api/auth/feishu/callback/` | GET | 飞书回调，建用户 + 一次性 code 跳前端（**v3.1 不直返 JWT**） |
| `/api/auth/feishu/exchange/` | POST | **v3.1 新增**：前端用一次性 code 换 JWT |
| `/api/auth/refresh/` | POST | JWT 刷新 |
| `/api/auth/me/` | GET | 当前用户信息 |

**BBS API**（Phase 3）：
| Endpoint | Method | 用途 |
|---|---|---|
| `/api/bbs/topics/` | GET / POST | 列表/发帖 |
| `/api/bbs/topics/<id>/` | GET / PATCH / DELETE | 详情/编辑/删除 |
| `/api/bbs/topics/<id>/replies/` | GET / POST | 楼层列表/回复 |
| `/api/bbs/likes/` | POST | 点赞 toggle |
| `/api/bbs/my/` | GET | 我的发帖/回复 |

**Contest API**（Phase 4）：见 v2

**UEditor API**：
- `/api/ueditor/config/`
- `/api/ueditor/upload/`
- `/api/ueditor/listimage/`
- `/api/ueditor/catchimage/`

#### 2.1.4 UEditor 上传接口（关键）

`apps/common/views_ueditor.py` 实现 4 个端点，详见 v2，**重点说明**：
- dev 期：`web/src/middlewares/ueditor.js`（已保留）继续作 Vite middleware mock
- prod 期：Django view 实现，存 COS
- 前端 `ContentEditor.vue` 通过 `serverUrl` 自动切换

#### 2.1.5 飞书 OAuth 鉴权（v3.1 修正：国内版端点）

> **v3 错误**：原写 `passport.feishu.cn/suite/passport/oauth/*`（Lark 国际版）。
> **v3.1 修正**：沿用旧系统 [feishu_auth.py](file:///Users/fanfan/Library/Mobile%20Documents/com~apple~CloudDocs/CloverHub%2Bweb%E7%AE%A1%E7%90%86/main/blog_system/feishu_auth.py) 的**飞书国内版**端点 `open.feishu.cn/open-apis/...`。
> 两种账号体系不互通，**不能**混用。

**`apps/auth_custom/feishu.py`**（v3.1 修正版）：
```python
import requests
from django.conf import settings
from urllib.parse import urlencode

# 国内版端点（v3.1 修正）
FEISHU_BASE = 'https://open.feishu.cn'
LOGIN_AUTHORIZE_URL = f'{FEISHU_BASE}/open-apis/authen/v1/index'  # 用户授权页
TOKEN_URL = f'{FEISHU_BASE}/open-apis/authen/v2/oauth/token'        # code 换 token
USER_INFO_URL = f'{FEISHU_BASE}/open-apis/authen/v1/user_info'      # 拿用户信息
TENANT_TOKEN_URL = f'{FEISHU_BASE}/open-apis/auth/v3/tenant_access_token/internal'

# 注意 v3 用的是国际版 passport.feishu.cn，会要求切换账号体系，废弃。

def get_tenant_access_token():
    """内部应用获取 tenant_access_token（应用级 token，调任何 OpenAPI 前需要）"""
    resp = requests.post(TENANT_TOKEN_URL, json={
        'app_id': settings.FEISHU_APP_ID,
        'app_secret': settings.FEISHU_APP_SECRET,
    })
    data = resp.json()
    if data.get('code') != 0:
        raise Exception(f"feishu tenant token error: {data}")
    return data['tenant_access_token'], data['expire']

def get_authorize_url(redirect_uri, state):
    """生成用户授权页 URL"""
    params = {
        'app_id': settings.FEISHU_APP_ID,
        'redirect_uri': redirect_uri,
        'state': state,
        'scope': 'contact:user.id:readonly',  # 只读用户 ID
    }
    return f"{LOGIN_AUTHORIZE_URL}?{urlencode(params)}"

def exchange_code_for_user(code):
    """用 code 换 user_access_token + refresh_token"""
    resp = requests.post(TOKEN_URL, json={
        'grant_type': 'authorization_code',
        'code': code,
        'client_id': settings.FEISHU_APP_ID,
        'client_secret': settings.FEISHU_APP_SECRET,
        'redirect_uri': f"{settings.SITE_URL}/api/auth/feishu/callback/",
    })
    data = resp.json()
    if data.get('code') != 0:
        raise Exception(f"feishu token error: {data}")
    return data['access_token'], data.get('refresh_token')

def get_user_info(user_access_token):
    """用 user_access_token 拿用户基本信息"""
    resp = requests.get(USER_INFO_URL, headers={
        'Authorization': f'Bearer {user_access_token}'
    })
    data = resp.json()
    if data.get('code') != 0:
        raise Exception(f"feishu userinfo error: {data}")
    return data['data']  # {open_id, union_id, name, avatar_url, ...}
```

**`apps/auth_custom/views.py`**（v3.1 修正 + 配合 B3）：
```python
import uuid
from django.utils import timezone
from django.shortcuts import redirect
from django.core.cache import cache  # v3.1 用 cache 存一次性 code
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from .models import User
from .feishu import (get_authorize_url, exchange_code_for_user,
                     get_user_info)

# v3.1 修正：缓存 key 前缀
FEISHU_STATE_TTL = 600  # state 10 分钟
ONE_TIME_CODE_TTL = 60  # 一次性 code 1 分钟


class FeishuLoginView(APIView):
    """跳转到飞书授权页"""
    def get(self, request):
        state = uuid.uuid4().hex
        # v3.1 修正：用 cache 而非 session（避免 cookie/CSRF 问题）
        cache.set(f'feishu_state:{state}', True, FEISHU_STATE_TTL)
        return redirect(get_authorize_url(
            f"{settings.SITE_URL}/api/auth/feishu/callback/",
            state
        ))


class FeishuCallbackView(APIView):
    """
    飞书回调
    v3.1 修正 B3：不直接把 JWT 放 URL 跳前端，而是：
      1. 校验 state
      2. 用 code 换 user_access_token
      3. 查/建用户
      4. 颁发内部 JWT + 一次性 6 位 code 存 cache
      5. 重定向到前端 /admin/login-success?code=XXXXXX
      6. 前端拿到 code 后 POST /api/auth/feishu/exchange/ 换 JWT
    """
    def get(self, request):
        code = request.GET.get('code')
        state = request.GET.get('state')

        # 1. 校验 state
        if not cache.get(f'feishu_state:{state}'):
            return Response({'error': 'invalid or expired state'}, status=400)
        cache.delete(f'feishu_state:{state}')

        try:
            # 2. 换 user_access_token
            user_access_token, _ = exchange_code_for_user(code)

            # 3. 拿用户信息
            user_info = get_user_info(user_access_token)
            open_id = user_info.get('open_id')
            union_id = user_info.get('union_id')

            # 4. 白名单
            allowed = settings.FEISHU_ALLOWED_OPENIDS
            if allowed and open_id not in allowed:
                return redirect(f"{settings.FRONTEND_URL}/admin/login-denied")

            # 5. 查/建用户
            user, created = User.objects.get_or_create(
                feishu_open_id=open_id,
                defaults={
                    'username': f'feishu_{open_id[:8]}',
                    'feishu_union_id': union_id,
                    'display_name': user_info.get('name', ''),
                    'avatar_url': user_info.get('avatar_url', ''),
                    'is_feishu_user': True,
                }
            )
            if not created:
                user.last_login_at = timezone.now()
                user.save(update_fields=['last_login_at'])

            # 6. 颁发 JWT + 一次性 code
            refresh = RefreshToken.for_user(user)
            jwt_access = str(refresh.access_token)
            one_time_code = uuid.uuid4().hex[:8].upper()
            cache.set(f'feishu_otc:{one_time_code}', {
                'user_id': user.id,
                'jwt': jwt_access,
                'refresh': str(refresh),
            }, ONE_TIME_CODE_TTL)

            return redirect(f"{settings.FRONTEND_URL}/admin/login-success?code={one_time_code}")

        except Exception as e:
            return Response({'error': str(e)}, status=500)


class FeishuExchangeView(APIView):
    """v3.1 修正 B3：前端用一次性 code 换 JWT"""
    def post(self, request):
        code = request.data.get('code')
        data = cache.get(f'feishu_otc:{code}')
        if not data:
            return Response({'error': 'invalid or expired code'}, status=400)
        cache.delete(f'feishu_otc:{code}')  # 一次性
        return Response({
            'access': data['jwt'],
            'refresh': data['refresh'],
            'user_id': data['user_id'],
        })
```

**前端配套**（v3.1）：
- `login-success` 页面 JS 读 URL `?code=...` → POST `/api/auth/feishu/exchange/` → 存到 Pinia store
- axios 拦截器从 store 读 token，不再从 URL 读

**CORS 配置补充**：
- `cache` 需配置 backend：`CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}`（dev）或 redis（prod）
- v3.1 默认 dev 用 LocMemCache（`backend/settings/dev.py`），prod 切 redis

**白名单机制**（保留 v3 设计）：
```python
# settings/base.py
FEISHU_ALLOWED_OPENIDS = os.getenv('FEISHU_ALLOWED_OPENIDS', '').split(',')
```

#### 2.1.6 CORS 配置

```python
CORS_ALLOWED_ORIGINS = [
    "https://communitygarden.org.cn",
    "https://www.communitygarden.org.cn",
    "http://localhost:3000",
    "http://localhost:5173",
]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = [
    "https://communitygarden.org.cn",
    "https://www.communitygarden.org.cn",
]
ALLOWED_HOSTS = [".communitygarden.org.cn", "localhost", "127.0.0.1"]
```

#### 2.1.7 settings 结构

```
backend/settings/
├── base.py       # 公共
├── dev.py        # DEBUG=True, console email
└── prod.py       # DEBUG=False, real config
```

`base.py` 关键项：
```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'apps.auth_custom',
    'apps.content',
    'apps.team',
    'apps.bbs',
    'apps.contest',
    'apps.common',
]

AUTH_USER_MODEL = 'auth_custom.User'

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'cloverweb'),
        'USER': os.getenv('DB_USER', 'cloverweb'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', '127.0.0.1'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# COS
COS_SECRET_ID = os.getenv('COS_SECRET_ID')
COS_SECRET_KEY = os.getenv('COS_SECRET_KEY')
COS_REGION = os.getenv('COS_REGION', 'ap-shanghai')
COS_BUCKET = os.getenv('COS_BUCKET', 'images-community')
UEditor_CONFIG = {
    'URL_PREFIX': os.getenv('UEditor_URL_PREFIX', 'https://images.communitygarden.org.cn'),
}

# 飞书 OAuth
FEISHU_APP_ID = os.getenv('FEISHU_APP_ID')
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_ALLOWED_OPENIDS = os.getenv('FEISHU_ALLOWED_OPENIDS', '').split(',')
SITE_URL = os.getenv('SITE_URL', 'https://communitygarden.org.cn')
FRONTEND_URL = os.getenv('FRONTEND_URL', SITE_URL)
```

### 2.2 前端：`web/`（重命名 `web-admin`）

#### 2.2.1 重命名 + git 仓库初始化（v3.1 修正 A2）

> **v3 错误**：用 `git mv web-admin web`。
> **v3.1 修正**：根目录**不是 git 仓库**（`web-admin/` 自己是独立仓库），`git mv` 会失败。
> 应改用普通 `mv`（`.git` 目录跟着走，web-admin 的提交历史不丢），并**新建根目录 git 仓库**以便 CI/CD 用。

```bash
# Step 1: 普通 mv（不丢 web-admin/.git 历史）
cd ~/Library/Mobile\ Documents/com~apple~CloudDocs/CloverHub+web管理
mv web-admin web
# 此时 web/.git 还在，是 web-admin 的 git 历史

# Step 2: 初始化根目录 git 仓库（v3.1 新增）
cd ~/Library/Mobile\ Documents/com~apple~CloudDocs/CloverHub+web管理
git init
git add .
git commit -m "init: 根仓库（包含 web/ backend/ deploy/ archive/ .github/）"

# Step 3: web/ 内的 .git 处理（二选一）
# 方案 A：保留 web/ 的 .git 作为子模块
#   优点：web/ 提交历史完全独立
#   缺点：CI/CD 要处理 submodule
# 方案 B（推荐）：删 web/.git，纳入根仓库统一管理
#   优点：CI/CD 简单
#   缺点：web-admin 历史合并到一条 init commit
rm -rf web/.git
git add web/
git commit -m "refactor: 合并 web-admin 历史到主仓库"

# Step 4: .gitignore
cat > .gitignore <<'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
venv/
*.sqlite3
.env
.coverage
.pytest_cache/

# Node
node_modules/
dist/
*.log
.DS_Store

# IDE
.vscode/
.idea/

# 构建产物
*.tar.gz
*.zip
EOF
```

**CI/CD 仓库路径要求**（v3.1 修正）：
- 根仓库 = `~/.../CloverHub+web管理/`
- push 触发后 GitHub Actions 拉这个根仓库
- `.github/workflows/deploy.yml` 在根仓库根目录
- SSH 到 CVM 部署时同步 `backend/ web/ deploy/ .env.example` 几个目录

> **历史合并说明**：web-admin 原 git 仓库的 14 条 commit 会从根仓库的提交历史中消失（删 `.git` 后整个 web/ 视为一次新提交）。如要保留：
> 1. 先 `mv web-admin web`（不删 .git）
> 2. 在根仓库里 `git subtree add --prefix=web /path/to/old/web-admin/.git HEAD`
> 3. 删 web/.git 后续 add
> 此方案 5 分钟内可完成。

#### 2.2.2 v3 关键改动：静态页内容迁入

**Step 1：提取 main/ 三个 HTML 的内容到 JSON 中间文件**

```bash
# 写脚本 main_html_to_json.py（一次性）
# 读 index.html / clover.html / philosophy.html
# 提取 <body> 内部 HTML、相关资源 URL
# 写 sitepages_seed.json
```

输出格式：
```json
{
  "home_legacy": {
    "title": "首页（legacy 备份）",
    "content_html": "<section>...</section>"
  },
  "about": {
    "title": "关于四叶草堂",
    "content_html": "<div>...</div>"
  },
  "philosophy": {
    "title": "我们的理念",
    "content_html": "<div>...</div>"
  }
}
```

**Step 2：用 Django 种子数据写库**

`backend/scripts/seed_initial_data.py`：
```python
"""
一次性脚本：把 sitepages_seed.json 写入 SitePage 表
用法：python manage.py shell < scripts/seed_initial_data.py
"""
import json
from apps.team.models import SitePage

with open('scripts/sitepages_seed.json') as f:
    data = json.load(f)

for slug, payload in data.items():
    SitePage.objects.update_or_create(
        slug=slug,
        defaults={
            'title': payload['title'],
            'content_html': payload['content_html'],
        }
    )
    print(f"✓ {slug}")

print(f"\n共导入 {len(data)} 个静态页")
```

**Step 3：Vue 端从 API 渲染**

`web/src/views/Home.vue`（v3 新版）：
```vue
<template>
  <div class="home-page">
    <SiteHeader />
    <main v-html="pageContent" />
    <SiteFooter />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import SiteHeader from '@/components/SiteHeader.vue'
import SiteFooter from '@/components/SiteFooter.vue'
import api from '@/api'

const pageContent = ref('')
onMounted(async () => {
  const { data } = await api.get('/sitepage/home/')
  pageContent.value = data.content_html
})
</script>
```

`About.vue` / `Philosophy.vue` 同理，调 `/sitepage/about/` 和 `/sitepage/philosophy/`。

**Step 4：清理 main/ 静态页**

迁入完成后，`main/index.html` / `clover.html` / `philosophy.html` 3 个文件不再用。Phase 2.7 整体归档 main/ 时会一起 tar。

#### 2.2.3 关键改动（cloud.js → axios）

`src/api/index.js`（新建）：
```js
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  timeout: 15000,
})

api.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.token) {
    config.headers.Authorization = `Bearer ${auth.token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    if (err.response?.status === 401) {
      // 跳飞书登录
      window.location.href = '/api/auth/feishu/login/'
    }
    return Promise.reject(err)
  }
)

export default api
```

`src/api/article.js`：从 CloudBase 改 axios
`src/cloud.js`：删除

#### 2.2.4 UEditor 集成（保留并接入 Django）

`src/components/content-editor/UEditor.vue` 改 `serverUrl`：
```js
const UEditor = window.UE.getEditor(this.id, {
  serverUrl: import.meta.env.VITE_UEDITOR_SERVER || '/api/ueditor/',
  // ... 原有配置保留
})
```

`vite.config.js`：
```js
server: {
  proxy: {
    '/api': 'http://127.0.0.1:8000',
  }
}
```

#### 2.2.5 新增 CMS 后台路由

`src/router/index.js`：
```js
const routes = [
  { path: '/', name: 'Home', component: () => import('@/views/Home.vue') },
  { path: '/about', name: 'About', component: () => import('@/views/About.vue') },
  { path: '/philosophy', name: 'Philosophy', component: () => import('@/views/Philosophy.vue') },
  { path: '/news', name: 'NewsList', component: () => import('@/views/News.vue') },
  { path: '/news/:slug', name: 'Article', component: () => import('@/views/Article.vue') },
  // CMS
  {
    path: '/admin',
    component: () => import('@/components/CmsLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/admin/articles' },
      { path: 'articles', name: 'AdminArticleList', component: () => import('@/views/admin/ArticleList.vue') },
      { path: 'articles/edit/:id?', name: 'AdminArticleEdit', component: () => import('@/views/admin/ArticleEdit.vue') },
      { path: 'sitepages', name: 'AdminSitePage', component: () => import('@/views/admin/SitePageEdit.vue') },
      { path: 'media', name: 'AdminMedia', component: () => import('@/views/admin/Media.vue') },
    ]
  },
  // Django admin 嵌入
  { path: '/django-admin/:path*', name: 'DjangoAdmin', component: () => import('@/views/admin/DjangoAdminEmbed.vue') },
]
```

#### 2.2.6 新增 CMS 视图

```
src/views/admin/
├── ArticleList.vue       # 列表（axios 调 /api/admin/articles/）
├── ArticleEdit.vue       # 编辑（嵌入 UEditor）
├── SitePageEdit.vue      # v3 新增：静态页编辑（关于 / 理念 等）
├── Media.vue             # 媒体库
└── DjangoAdminEmbed.vue  # iframe 嵌入 /django-admin/
```

`SitePageEdit.vue`（v3 新增）：
```vue
<template>
  <el-form>
    <el-form-item label="Slug">
      <el-select v-model="form.slug">
        <el-option label="首页" value="home" />
        <el-option label="关于" value="about" />
        <el-option label="理念" value="philosophy" />
      </el-select>
    </el-form-item>
    <el-form-item label="标题">
      <el-input v-model="form.title" />
    </el-form-item>
    <el-form-item label="内容">
      <ContentEditor v-model="form.content_html" />
    </el-form-item>
    <el-button @click="save">保存</el-button>
  </el-form>
</template>
```

#### 2.2.7 package.json 调整

删除：
- `@cloudbase/js-sdk`
- `@cloudbase/framework-plugin-website`

保留：
- `vue`、`vue-router`、`element-plus`、`xlsx`、`file-saver`
- `@vitejs/plugin-vue`、`vite`

新增：
- `pinia`
- `axios`

#### 2.2.8 vite.config.js（v3.1 修正 A3 + 路由 B1）

> **A3 修正**：`public/UEditorPlus/ueditor.all.js` 是 public 资源（运行时通过 `<script src="/UEditorPlus/ueditor.all.js">` 加载），**不进 rollup 打包管线**。把它放进 `manualChunks` 永远是空 chunk，已删除。
>
> **B1 修正**：路由从 `createWebHashHistory` 改 `createWebHistory`，配合 Nginx `try_files` 支持真实 URL（SEO 必需）。

```js
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import ueditorMiddleware from './src/middlewares/ueditor.js'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd())
  return {
    plugins: [vue(), ueditorMiddleware()],
    resolve: { alias: { '@': path.resolve(__dirname, './src') } },
    server: {
      port: 3000,
      proxy: {
        '/api': 'http://127.0.0.1:8000',
      }
    },
    build: {
      rollupOptions: {
        output: {
          // v3.1 修正 A3：UEditorPlus 走 public，不进 manualChunks
          // 避免误导性的空 chunk
          manualChunks: {
            'vue-vendor': ['vue', 'vue-router', 'pinia'],
            'element-vendor': ['element-plus', '@element-plus/icons-vue'],
            'axios-vendor': ['axios'],
          }
        }
      }
    }
  }
})
```

**配套 src/router/index.js 修正 B1**：
```js
import { createRouter, createWebHistory } from 'vue-router'  // v3.1 改 history 模式

const routes = [
  { path: '/', name: 'Home', component: () => import('@/views/Home.vue') },
  { path: '/about', name: 'About', component: () => import('@/views/About.vue') },
  { path: '/philosophy', name: 'Philosophy', component: () => import('@/views/Philosophy.vue') },
  { path: '/news', name: 'NewsList', component: () => import('@/views/News.vue') },
  { path: '/news/:slug', name: 'Article', component: () => import('@/views/Article.vue') },
  // ... admin 路由
]

const router = createRouter({
  // v3.1 修正 B1：用 history 模式，URL 形如 /news/clover-park
  // SEO 友好，但需 Nginx try_files 配置（已在 nginx.conf 2.3.3 中）
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    return { top: 0 }
  }
})

export default router
```

**Nginx 配套**（v3.1 已包含，见 2.3.3）：
```nginx
location / {
    root /home/cloverweb/web/dist;
    try_files $uri $uri/ /index.html;  # history 模式必须
    expires 1d;
}
```

**hash vs history 对比**（为什么必须改）：
| 模式 | URL 形如 | 搜索引擎 | 分享友好 |
|---|---|---|---|
| hash（v3） | `/#/news/clover-park` | ❌ 不收录 | ❌ 难看 |
| history（B1） | `/news/clover-park` | ✅ 收录 | ✅ 干净 |

### 2.3 部署基础设施

#### 2.3.1 CVM 准备（2C2G）

```bash
# 初始化
sudo apt update && sudo apt install -y python3.11 python3.11-venv nginx postgresql postgresql-client certbot python3-certbot-nginx git

# PostgreSQL
sudo -u postgres createuser cloverweb -P
sudo -u postgres createdb cloverweb -O cloverweb

# 部署用户
sudo useradd -m -s /bin/bash cloverweb
sudo mkdir -p /home/cloverweb
sudo chown cloverweb:cloverweb /home/cloverweb

# 目录结构
sudo -u cloverweb mkdir -p /home/cloverweb/{backend,web,staticfiles,media,logs,backups}
```

#### 2.3.2 systemd 单元

`deploy/cloverweb-web.service`：
```ini
[Unit]
Description=CloverWeb (Django + Gunicorn)
After=network.target postgresql.service

[Service]
User=cloverweb
Group=cloverweb
WorkingDirectory=/home/cloverweb/backend
Environment="PATH=/home/cloverweb/backend/venv/bin"
EnvironmentFile=/home/cloverweb/.env
ExecStart=/home/cloverweb/backend/venv/bin/gunicorn cloverweb.wsgi:application \
  --workers 1 --threads 4 \
  --bind 127.0.0.1:8000 \
  --access-logfile /home/cloverweb/logs/access.log \
  --error-logfile /home/cloverweb/logs/error.log \
  --max-requests 1000 --max-requests-jitter 100
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

#### 2.3.3 Nginx 配置（v3 无旧站共存版）

`deploy/nginx.conf`：
```nginx
upstream cloverweb_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name communitygarden.org.cn www.communitygarden.org.cn;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name communitygarden.org.cn www.communitygarden.org.cn;

    ssl_certificate /etc/letsencrypt/live/communitygarden.org.cn/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/communitygarden.org.cn/privkey.pem;

    client_max_body_size 20M;

    # 前端静态资源
    location / {
        root /home/cloverweb/web/dist;
        try_files $uri $uri/ /index.html;
        expires 1d;
    }

    # Django API
    location /api/ {
        proxy_pass http://cloverweb_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Django admin（iframe 嵌入用）
    location /django-admin/ {
        proxy_pass http://cloverweb_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Django static/media
    location /static/ {
        alias /home/cloverweb/staticfiles/;
        expires 30d;
    }
    location /media/ {
        alias /home/cloverweb/media/;
        expires 7d;
    }
}
```

> v3 关键变化：移除 `/blog-old/` 反代（main/ 整体归档，不再共存）

#### 2.3.4 静态资源 + 媒体文件

- 前端构建产物：`web/dist/` 由 Nginx 直出
- Django `collectstatic` 产物：`/home/cloverweb/staticfiles/` 由 Nginx 直出
- 用户上传：通过 UEditor 接口走 COS，**不落本地**

#### 2.3.5 数据库备份策略

`deploy/backup.sh`（cron 每日 2:00 跑）：
```bash
#!/bin/bash
BACKUP_DIR=/home/cloverweb/backups/db
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME=cloverweb_${DATE}.sql.gz
mkdir -p $BACKUP_DIR
sudo -u postgres pg_dump cloverweb | gzip > $BACKUP_DIR/$FILENAME
find $BACKUP_DIR -name "cloverweb_*.sql.gz" -mtime +7 -delete
```

#### 2.3.6 监控与告警

- 腾讯云监控（CPU/内存/磁盘/网络）— 免费基础版
- `Uptime Kuma` 自部署监控：
  - `https://communitygarden.org.cn/` 200
  - `https://communitygarden.org.cn/api/articles/`
  - `https://communitygarden.org.cn/django-admin/login/`
- 告警：腾讯云短信/邮件

### 2.4 CI/CD（v3.1 修正 B2）

> **v3 风险**：deploy job 在 CVM 上跑 `npm ci && npm run build`，Vite 构建 Vue3+ElementPlus 峰值内存 1GB+，**2C2G 同时跑 Django+PG+Nginx 容易 OOM**。
> **v3.1 修正**：test job 已经在 GitHub Actions runner 上构建并 upload artifact，**deploy job 改为 scp artifact 到 CVM**，CVM 只解压不构建。

#### 2.4.1 GitHub Actions workflow（v3.1 修正 B2）

`.github/workflows/deploy.yml`：
```yaml
name: Deploy to CVM
on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: cloverweb_test
          POSTGRES_USER: cloverweb
          POSTGRES_PASSWORD: test
        ports: ['5432:5432']
        options: --health-cmd pg_isready --health-interval 10s
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: |
          cd backend
          python -m venv venv
          source venv/bin/activate
          pip install -r requirements.txt
          pip install pytest pytest-django
          pytest
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: |
          cd web
          npm ci
          npm run build
      # v3.1 修正 B2：把构建产物 upload 给 deploy job
      - uses: actions/upload-artifact@v4
        with:
          name: web-dist
          path: web/dist/
          retention-days: 7

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4

      # 1. 下载 web 构建产物
      - uses: actions/download-artifact@v4
        with:
          name: web-dist
          path: dist/

      # 2. 同步 backend + deploy + dist 到 CVM
      - name: Sync to CVM
        uses: appleboy/scp-action@v0.1.7
        with:
          host: ${{ secrets.CVM_HOST }}
          username: ${{ secrets.CVM_USER }}
          key: ${{ secrets.CVM_SSH_KEY }}
          source: "backend/,deploy/,dist/,requirements.txt"
          target: /home/cloverweb/

      # 3. v3.1 修正 B2：CVM 不再 build
      - name: Deploy on CVM
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.CVM_HOST }}
          username: ${{ secrets.CVM_USER }}
          key: ${{ secrets.CVM_SSH_KEY }}
          script: |
            set -e
            cd /home/cloverweb

            # 后端依赖更新
            cd backend
            source venv/bin/activate
            pip install -r requirements.txt
            python manage.py migrate --noinput
            python manage.py collectstatic --noinput
            cd ..

            # v3.1 修正 B2：dist 直接从 CI 解压（不 npm build）
            rm -rf web/dist
            mv dist web/dist

            # 重启服务
            sudo systemctl restart cloverweb-web
            sudo systemctl reload nginx
            echo "Deployed at $(date)"
            free -h  # 监控内存，便于后续排查
```

**CVM 上的内存预算**（v3.1 修正后）：
| 进程 | 内存 |
|---|---|
| OS + 系统 | 300 MB |
| Nginx | 20 MB |
| PostgreSQL | 250 MB |
| Redis (Phase 3) | 80 MB |
| Gunicorn (1 worker + 4 threads) | 350 MB |
| **总计** | **~1.0 GB** |
| **剩余** | **~1.0 GB 余量** |

不构建前端后，留出约 1GB buffer，应对突发流量或缓存增长。如果将来 4C4G，可上 2 worker + 1 个 Celery worker。

#### 2.4.2 必要的 GitHub Secrets

| Secret | 用途 |
|---|---|
| `CVM_HOST` | CVM 公网 IP |
| `CVM_USER` | 部署用户（`cloverweb`） |
| `CVM_SSH_KEY` | 私钥 |
| `DB_PASSWORD` | PostgreSQL 密码 |
| `COS_SECRET_ID` | COS 访问 |
| `COS_SECRET_KEY` | COS 访问 |
| `JWT_SECRET` | JWT 签名密钥 |
| `FEISHU_APP_ID` | 飞书 OAuth |
| `FEISHU_APP_SECRET` | 飞书 OAuth |
| `FEISHU_ALLOWED_OPENIDS` | 飞书白名单 |

#### 2.4.3 回滚策略

- CVM 上保留 `releases/` 目录，最近 3 个版本
- `cloverweb-web.service` 启动时通过 `Environment="APP_VERSION=..."` 切版本
- 一键回滚：`deploy/rollback.sh <version>`

### 2.5 数据迁移：v3 = 从零开始

**v3 决策：不写数据迁移脚本**（v2 方案作废）。

| 数据源 | 处置 |
|---|---|
| CloudBase `articles` 集合 | **不迁**。新站从零开始 |
| main/blog_system SQLite | **不迁**。数据很少 |
| main/index.html / clover.html / philosophy.html | **内容迁 SitePage**（见 2.2.2） |
| 关键活动卡片（如"第六届竞赛"） | 手动在 Django admin 创建 5-10 条 Article |
| 飞书 OAuth 配置 | 重新配置到新 app，复用旧 `FEISHU_APP_ID/SECRET` 即可（如果保留旧 app） |

**初始化种子数据脚本**：`backend/scripts/seed_initial_data.py`（见 2.2.2）。

### 2.6 测试策略

- **后端**：pytest + pytest-django，每个 app 一个 `tests/`
- **前端**：关键路径手动测试 + 可选 playwright
- **性能**：2C2G 上单 worker + 4 threads，首页 P95 < 500ms

### 2.7 main/ 归档（v3 新增步骤）

完成 2.1-2.6 后，执行归档：

```bash
# 1. 备份
mkdir -p archive
cd ..
tar czf CloverHub+/web管理/archive/main-2026-08-xx.tar.gz CloverHub+/web管理/main/
# 2. 验证 tar 包可解压
tar tzf archive/main-2026-08-xx.tar.gz | head
# 3. 删除原 main 目录
rm -rf CloverHub+/web管理/main/
# 4. 写归档说明
cat > archive/ARCHIVE.md <<'EOF'
# main/ 归档说明

归档时间：2026-08-xx
归档原因：网站重构完成，旧 Flask 博客不再使用

包含：
- main/index.html / clover.html / philosophy.html 内容已迁到新系统 SitePage 表
- main/blog_system/ Flask 源码（Vditor 编辑器，保留作参考）
- main/blog_system/ 工时系统（用户已备份到其他地方）
- main/ppt_project/ PPT 设计稿
- main/docs/ 项目文档

解包命令：
  tar xzf main-2026-08-xx.tar.gz

如需回退：
  1. 解包到原位置
  2. 重新启动 main/blog_system 的 gunicorn（如果 CVM 还在跑）
EOF
```

**触发条件**：2.2.2 静态页内容已成功迁入 SitePage，且新站已上线 1 周无故障。

---

## 三、Phase 3：BBS 论坛（Week 9-12）

> 决策：自建在 Django `apps/bbs/`，复用 web/ 前端栈。

### 3.1 数据模型
见 2.1.2

### 3.2 API
见 2.1.3

### 3.3 前端
- `web/src/views/bbs/{Index,Topic,NewTopic}.vue`
- 路由：`/bbs`, `/bbs/topic/:id`, `/bbs/new`
- 顶部导航加"社区"入口
- UEditorPlus 集成（接 2.1.4 实现的 Django 接口）

### 3.4 鉴权
- 公开用户：邮箱注册 + 邮箱验证
- 可选：飞书 OAuth 快速登录
- 暂不接第三方实人 API

---

## 四、Phase 4：社区花园竞赛服务（Week 13+，持续）

> 决策：自建，数据模型 + 后台用 Django 已有 app `contest/`。

### 4.1 数据模型
见 2.1.2

### 4.2 复用现有 UI
- `web/src/views/Home.vue` 的"全国社区花园设计营造竞赛与社区参与行动"section 卡片
- "第六届 · 报名进行中" 按钮链向 `/contest/2026`
- `web/src/views/contest/{Home,Register,Detail,Rank}.vue` 新增

### 4.3 后台
- Django admin 管 Season/Team/Submission
- 评委打分前端简单页面
- 排行榜用 `django-q2` 定时任务每 5 分钟刷新 `Ranking` 表

---

## 五、里程碑与时间线（v3）

| 周 | 任务 | 验收 |
|---|---|---|
| 1-2 | ✅ Phase 1：删除小程序 + 清理 web-admin 后台 + 恢复 main | `web/` 仅含公共部分 + UEditor；build 通过 |
| 3-4 | Phase 2.1：Django 项目初始化 + 全部模型 + DRF + 飞书 OAuth | 本地起服务，admin 可登录，OAuth 跑通 |
| 5 | Phase 2.1.4：UEditor 上传接口实现 | UEditor dev + prod 都能上传到 COS |
| 6 | Phase 2.2：web/ 前端改 axios + 静态页内容迁入 + 嵌入 Django admin | 前端能列出文章、点开详情，CMS 后台能编辑文章，Home/About/Philosophy 内容显示 |
| 7 | Phase 2.3：CVM 部署 + Nginx + systemd | `https://communitygarden.org.cn` 跑通 |
| 8 | Phase 2.5-2.6：种子数据 + 上线 1 周观察 | 新站稳定运行，文章可见，CMS 正常 |
| 8（末） | Phase 2.7：main/ 归档 | `archive/main-2026-08-xx.tar.gz` 存在，`main/` 已删 |
| 9-10 | Phase 3：BBS 后端 + 前端 | 用户能注册、发帖、回复 |
| 11-12 | Phase 3：BBS 完善（点赞、嵌套回复、搜索） | UI 走通 |
| 13+ | Phase 4：竞赛服务 | 持续 |

---

## 六、风险与备选方案

| 风险 | 影响 | 备选 |
|---|---|---|
| 飞书 OAuth 配置失败 | 内部无法登录 | 临时方案：邮箱密码登录（已在 User 模型扩展） |
| UEditorPlus 上传到 CVM 跨域问题 | 编辑器上传失败 | nginx CORS 头 + COS 桶 CORS 规则 |
| 静态页迁入后样式不一致 | 用户体验差 | 提取 main 静态页的 CSS 到 web 的 styles/ 目录 |
| 2C2G 性能不够 | 频繁 OOM | 升级到 4C4G（约 +100 元/月） |
| 邮件 SMTP 被退信 | 邮箱验证失败 | 切换到腾讯云 SES / SendGrid |
| COS 跨域上传签名过期 | 编辑器上传失败 | 临时 token（5min 过期） |
| BBS 实名合规要求 | 监管风险 | 加手机号验证；暂不接第三方实人 API |
| main/ 归档后想回退 | 重新部署旧站 | tar 包已保留，按 ARCHIVE.md 步骤解包 |

---

## 七、不在本计划范围

- 微信小程序本身：保持 CloudBase 现状，不动其运行环境
- **工时系统**：用户已备份，将单独部署到其他地方
- **Vditor**：旧代码，不用
- **旧 main/blog_system 整目录**：归档后不再用
- **CloudBase 旧 articles 集合**：不迁，2 周后清理
- **CloudBase 旧 cloudfunctions（7 个）**：不删，2 周后清理
- 旧版 blog_system 的工时数据：用户已备份

---

## 八、需要你确认的决策（v3 全部已决）

| # | 项 | **v3 决定** | 理由 |
|---|---|---|---|
| 1 | main/ 处置 | **整体归档**（Phase 2.7） | 静态页已迁 Vue，blog_system 不再需要 |
| 2 | CMS 后台方案 | **Django admin 套 UEditorPlus iframe** | 省工作量 |
| 3 | CMS 鉴权 | **飞书 OAuth** | 内部员工统一用飞书 |
| 4 | BBS 鉴权 | **邮箱注册 + 飞书 OAuth 可选** | 公开用户 |
| 5 | 域名 | **继续 `communitygarden.org.cn`** | 保留 SEO |
| 6 | 旧 CloudBase 保留时长 | **2 周** | 资源免费 |
| 7 | PostgreSQL 部署 | **CVM 本地盘** | 省钱 |
| 8 | 编辑器 | **UEditorPlus**（不用 Vditor） | 你已确认 |
| 9 | 移动端适配 | **自适应** | 工作量小 |
| 10 | 监控 | **腾讯云监控 + Uptime Kuma** | 2C2G 跑不动 Prometheus |
| 11 | **静态页迁移** | **A. 迁 Vue 组件**（你已确认） | 单一前端栈 |
| 12 | **CloudBase 数据迁移** | **不迁** | 仅有封面+标题 |
| 13 | **SQLite 迁移** | **不迁** | 数据很少 |
| 14 | **工时系统** | **不迁**，单独部署 | 与主体无关 |

**v3 决策全部锁定，可进入执行阶段**。

---

## 九、最终验收（v3）

- [ ] `wechat-mini-program/` 物理删除
- [ ] `web-admin/` 改名 `web/`
- [ ] `backend/` Django 项目跑通：文章 CRUD、SitePage 管理、BBS 发帖/回复、竞赛季管理
- [ ] **UEditorPlus 在新系统正常工作**（图片/视频/公式上传到 COS）
- [ ] **飞书 OAuth 登录跑通**（内部员工可登录 CMS）
- [ ] **Home/About/Philosophy 静态页内容从 SitePage 渲染**
- [ ] CVM 部署跑通，HTTPS 可访问
- [ ] CloudBase `articles` 集合 2 周后清理
- [ ] CloudBase 旧 cloudfunctions 2 周后清理
- [ ] **小**程序仍在 CloudBase 上独立运行，**不**受本次重构影响
- [ ] `main/` 整体归档到 `archive/main-2026-08-xx.tar.gz`，原目录删除
- [ ] CI/CD：push main → 自动部署到 CVM
- [ ] 数据库每日自动备份到 `/home/cloverweb/backups/db/`
- [ ] 监控告警正常
- [ ] 工时系统单独部署到其他环境（用户自处理）

---

## 十、Phase 2 第 1 步执行清单（v3.1）

下一步即将执行的具体动作（你说"开始"就跑这套）：

```bash
# A2 修正：先重命名 web-admin → web（不丢历史）
cd ~/Library/Mobile\ Documents/com~apple~CloudDocs/CloverHub+web管理
mv web-admin web

# 1. 后端初始化
mkdir backend && cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
# 装包（见 2.1.1）
django-admin startproject cloverweb .
python manage.py startapp content
python manage.py startapp team
python manage.py startapp auth_custom
python manage.py startapp bbs
python manage.py startapp contest
python manage.py startapp common

# 2. 写 models.py（见 2.1.2）
# 3. 写 settings/ 结构（base/dev/prod）
# 4. python manage.py makemigrations
# 5. python manage.py migrate
# 6. python manage.py createsuperuser

# 7. 飞书 OAuth（v3.1 修正 A1 + B3 完整代码，见 2.1.5）

# 8. 验证前端 build
cd ../web
npm install
npm run build   # 验证 manualChunks 修正后 OK
```

预期产出：
- 本地 `backend/` 跑通 + 6 个 app + admin 可登录
- 飞书 OAuth 框架（4 个端点）
- 前端 build 通过（`vue-vendor` / `element-vendor` / `axios-vendor` 三个真实 chunk）
- `backend/` 和 `web/` 在根目录同级

**确认执行？**
- 答 **"开始"** / **"执行"** → 跑上述步骤
- 答 **"先看 X"** → 先看某个具体模块代码
- 答 **"调整"** → 改方案

---

## 十一、v3.1 修正日志

| 编号 | 类别 | v3 原内容 | v3.1 修正 |
|---|---|---|---|
| A1 | 错误 | 飞书端点用 `passport.feishu.cn`（国际版） | 改用 `open.feishu.cn/open-apis/...`（国内版，与旧系统一致） |
| A2 | 错误 | `git mv web-admin web`（根目录非 git 仓库会失败） | 改普通 `mv` + 根目录 `git init` + 保留 web-admin 历史的方案 |
| A3 | 错误 | `manualChunks` 含 `ueditor-vendor`（public/ 不进 rollup） | 删除该条，保留 vue/element/axios 三个真实 vendor |
| B1 | 高风险 | `createWebHashHistory` 无 SEO | 改 `createWebHistory`，配 Nginx `try_files` |
| B2 | 高风险 | CVM 上跑 `npm build` 易 OOM | CI 上 build，scp artifact 到 CVM，CVM 不构建 |
| B3 | 高风险 | 飞书回调 `?token=...` 直返 URL 有泄露风险 | 改一次性 code 中转 + 前端 POST 换 JWT |
| v3.2 | 命名 | 全篇 `cloverhub`（与小程序撞名） | 统一改 `cloverweb`；部署目录 `/srv/cloverhub` → `/home/cloverweb`；GitHub 仓库名不动 |

## 十二、v3.2 执行日志

- ✅ Phase 2 第 1 步已完成（2026-08-17）：`web-admin/` → `web/` 重命名；`backend/` Django 5 骨架 + 6 app + settings 三层结构 + 全部模型 + 飞书 OAuth 框架 + content 公开 API；`makemigrations`/`migrate`（SQLite dev）通过；superuser 已建（admin / clover2026web，建议尽快改密）；`web/` build 通过（4.03s）。
- ✅ Phase 2 第 2 步已完成（2026-08-17）：
  - **git 仓库**：web 旧历史打包至 `.trae/web-history-legacy.bundle` 后并入根仓库（baseline `3cfe977`）；根目录 `git init -b main` + `.gitignore`
  - **B1 路由**：`createWebHashHistory` → `createWebHistory` + `scrollBehavior`
  - **前端接线**：新增 `src/utils/request.js`（axios，baseURL=/api）+ `src/api/sitepage.js`；`src/api/article.js` 重写为 Django 版（snake_case→camelCase 映射、分页 list/total、slug 详情、浏览量后端自增）；`NewsList.vue` 剥离小程序 activities 混排；`ArticleDetail.vue` 改 slug；vite proxy `/api`→127.0.0.1:8000
  - **静态页迁移**：`seed_sitepages` 管理命令（tinycss2 做 CSS scope 变换，`*`/`:root`/`body` 特判，@media 递归，@keyframes/@font-face 保留）；三页写入 SitePage（home 12.6k / about 27k / philosophy 16.9k 字符，0 选择器泄漏）；旧 HomePage/AboutPage/PhilosophyPage 删除，新 `SitePageView.vue` 统一渲染
  - **验证**：API 200 ×4；vite build 2.94s；浏览器实测四页渲染 PASS（绿色主题/卡片/导航/页脚正常，外链图片 ORB 拦截为 CDN 跨域问题，非迁移缺陷）
- 待办遗留：C 类 XSS sanitize 待 BBS 上线前处理
- ✅ Phase 2 第 3 步已完成（2026-08-18）：**UEditorPlus 接 Django**
  - **后端**：`apps/common/cos.py`（COS 直传工具，凭证缺失抛 `CosNotConfigured`）+ `views_ueditor.py`（统一入口 `/api/ueditor/?action=`：config / uploadimage / uploadvideo / uploadfile / catchimage / listimage，`csrf_exempt`，上传记录入 `UploadedFile` 表）+ `urls.py` 注册；`settings/base.py` 加 `load_dotenv`；新增 `backend/.env.example`（COS 凭证模板，**待用户填写 COS_SECRET_ID/KEY/BUCKET 后上传才可用**）
  - **前端**：`content-editor/UEditor.vue` 去 `@/cloud` 依赖，`serverUrl: '/api/ueditor/'`，秀米图片转存改批量 POST 后端 `catchimage`（source[] 数组，带去重缓存）；删除旧 `getActionUrl` hook
  - **清理**：删 `web/src/cloud.js`、旧版 `web/src/components/UEditor.vue`、`web/src/utils/cos-upload.js`、`web/src/middlewares/ueditor.js`（dev 改走 vite proxy → Django）、`web/api/`（旧 node 上传）、`web/.env`（仅含 CloudBase ID）；`package.json` 删 `@cloudbase/js-sdk` + `@cloudbase/framework-plugin-website`；`vite.config.js` 重写（去 ueditorMiddleware/CloudBase define，补回 manualChunks 三 vendor）
  - **验证**：Django 接口测试 PASS（config 200 / listimage 200 / 未知 action FAIL / 非法扩展名拒绝 / 无 COS 凭证明确报错）；vite build 2.63s（vue/element/axios 三 chunk）；vite proxy 端到端 curl PASS
- ✅ Phase 2 第 4 步已完成（2026-08-18）：**CMS 后台前端 + 管理端 API**
  - **后端管理 API**：`content/admin_serializers.py`（ArticleAdminSerializer：category 按 slug、tags 名称列表自动 get_or_create、author 自动取当前用户；SitePageAdminSerializer）+ `content/admin_views.py`（/api/admin/articles/ CRUD、categories、sitepages，IsAdminUser 权限）+ `auth/token/`（simplejwt 密码换 JWT，dev 期/备用）
  - **bug 修复**：公开列表 `website_sections__contains` 在 SQLite 不支持（JSONField contains 仅 PG）→ 改 `icontains` 跨库通用
  - **前端 CMS**：`utils/auth.js`（JWT 存 localStorage）+ `request.js`（Bearer 拦截器，仅 /admin/* 401 强制重登）；`api/admin.js`；`CmsLayout.vue`（侧边栏布局）；`admin/Login.vue`（el-tabs 飞书/密码双模式）、`LoginCallback.vue`（一次性 code 换 JWT）、`ArticleList.vue`（筛选/搜索/发布撤回/精选开关/删除）、`ArticleEdit.vue`（集成 UEditorPlus，板块挂载 home_news）、`SitePageEdit.vue`（三静态页 UEditor 编辑）
  - **路由守卫**：/admin requiresAuth → 未登录跳 /admin/login；已登录访问登录页直达后台
  - **首页资讯卡片接线**：`SitePageView.vue` 渲染 home 后请求 `/api/articles/?section=home_news`，文章卡片前插静态 HTML 的 `.review-grid`（复用 review-card 样式，title 转义防 XSS）
  - **验证**：后端接口 9 项 PASS（401/登录/建分类/建文章含 tags+published_at 自动/section 过滤/PATCH/静态页 PUT/DELETE）；浏览器 E2E 10 步全 PASS（登录→建文→列表→首页卡片→详情→静态页编辑器）
- ✅ Phase 2 第 5 步已完成（2026-08-18）：**CVM 部署配置**
  - **`.github/workflows/deploy.yml`**：push main（backend/web/deploy 路径触发）+ workflow_dispatch；CI 内 node20 构建 web → dist 自检（index.html + UEditorPlus/）→ 打包（backend 源码排除 venv/.env/db.sqlite3/staticfiles + web/dist）→ scp 单 tar → ssh 免密 sudo 执行 deploy.sh → health check（gunicorn :8000 + systemctl is-active，带 Host 头）
  - **`deploy/deploy.sh`**（CVM 每次部署）：停服 → web 全量 rsync --delete（清旧 hash 产物）/ backend rsync 保留 venv+.env+staticfiles+media → pip install → 子 shell 内 source .env 后 migrate + collectstatic（规避 sudo env_reset）→ 重启
  - **`deploy/setup-server.sh`**（一次性初始化，9 步）：PGDG 装 PostgreSQL 16 + 2C2G 保守参数（shared_buffers 256MB/max_connections 60）→ 建 cloverweb 用户/目录/venv → 生成 backend/.env（随机 SECRET_KEY，DB 凭证）→ systemd + Nginx 启用 → certbot 签证书；另建 cloverweb-deploy CI 用户 + sudoers 白名单（仅 NOPASSWD deploy.sh）
  - **`deploy/systemd/cloverweb.service`**：gunicorn 2 workers × 2 threads @127.0.0.1:8000，EnvironmentFile=.env，MemoryMax 768M，ProtectSystem=full
  - **`deploy/nginx/cloverweb.conf`**：80 端口初版（certbot 自动升级 443）；`try_files $uri /index.html`（history 路由）；/assets/ 30d immutable；/api/ 反代 gunicorn（client_max_body_size 220m 供 UEditor 视频）；/static/ alias collectstatic；/django-admin/；gzip
  - **验证**：bash -n 全过、workflow YAML ruby 解析 OK、CI 打包本地演练（backend 91 + web 321 文件、0 敏感文件泄漏、UEditorPlus 在 dist）
  - **待用户操作**：①CVM 上跑 setup-server.sh（export DB_PASS/CERTBOT_EMAIL）②GitHub 仓库配 Secrets（SSH_HOST/SSH_USER=cloverweb-deploy/SSH_PRIVATE_KEY，可选 SSH_PORT）③CVM .env 补 COS 凭证 ④首次部署后验证 https://communitygarden.org.cn

C 类（XSS sanitize、SQLite 起步、settings 拆分、middleware 优先级）和 D 类（备份 sudoers、/media 冗余、域名备案、axios 已存在、django-admin 路由实现）保留到执行时处理。
