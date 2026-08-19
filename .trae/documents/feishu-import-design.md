# 飞书文档导入功能详细设计文档

> **v1.1 实施修正**（2026-08-19，与最终实现一致）：
> 1. **放弃 user OAuth，改用 tenant_access_token（应用凭证）模式**——现有 `/api/auth/feishu/callback/` 为 CMS 登录专用（硬约束，不侵入）；文档共享给应用后即可导入，无需 OAuth 回调与 token 刷新，去掉 FeishuToken 表。
> 2. **导入对话框放 Vue 层而非 UEditor iframe**——CMS 前端为 JWT 认证，iframe 内裸 fetch 无法携带 JWT；按钮通过 `UE.registerUI` 注册在工具栏（秀米旁），点击经 `window.__UE_FEISHU_IMPORT__` 回调桥接到 Vue 事件，打开 Element Plus 对话框。
> 3. 支持粘贴 docx / wiki 链接导入（wiki 自动解析 obj_token）；可选配置 `FEISHU_FOLDER_TOKEN` 浏览共享文件夹内文档列表。

## 一、功能概述

将飞书文档导入到 cloverweb 网站后台，转换为 UEditorPlus 兼容的 HTML 格式，支持用户在编辑器中预览和微调后保存为文章。

**核心价值**：
- 复用飞书作为内容创作平台的优势
- 与现有 UEditorPlus 编辑器无缝集成
- 支持图文混排、分栏布局等复杂格式
- 自动转存飞书图片到腾讯云 COS

---

## 二、系统架构

### 2.1 技术栈

| 层级 | 技术 | 说明 |
|---|---|---|
| 前端 | Vue 3 + UEditorPlus | 编辑器组件，工具栏集成飞书导入按钮 |
| 后端 | Django 5 + DRF | RESTful API，飞书 tenant token，文档解析 |
| 存储 | PostgreSQL + COS | 文章数据 + 图片资源 |
| 外部服务 | 飞书开放平台 | 文档读取 API（open.feishu.cn） |

### 2.2 模块划分（实际落地）

```
backend/apps/content/
├── models.py                    # 新增 FeishuDocument, FeishuImportLog
├── feishu_api.py                # 飞书文档 API 封装（tenant token / blocks / 图片下载）
├── feishu_parser.py             # Block 树 → HTML 转换器（含 Grid 并排图片）
├── feishu_views.py              # DRF API 视图
└── urls.py                      # 路由（追加 admin/feishu/*）

web/public/UEditorPlus/dialogs/feishu-connect/
└── feishu-ue-button.js          # UE.registerUI 工具栏按钮（含图标注入）

web/src/
├── components/FeishuImportDialog.vue   # Element Plus 导入对话框（Vue 层，JWT 认证）
├── components/content-editor/UEditor.vue       # 工具栏加 feishuimport + 事件桥接
├── components/content-editor/ContentEditor.vue # 转发 feishu-import 事件 + insertHtml
└── views/admin/ArticleEdit.vue / SitePageEdit.vue  # 接入对话框
```

---

## 三、数据模型设计（已迁移 0002）

### 3.1 FeishuDocument（飞书文档元数据）

```python
class FeishuDocument(models.Model):
    """飞书文档导入记录（tenant token 模式：文档需共享给应用）。"""
    doc_token = models.CharField('飞书文档 Token', max_length=128, unique=True, db_index=True)
    title = models.CharField('文档标题', max_length=300)
    source = models.CharField('链接类型', max_length=16, default='docx')  # docx / wiki
    article = models.ForeignKey(
        Article, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='feishu_docs', verbose_name='关联文章',
    )
    last_sync_at = models.DateTimeField('最后同步时间', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### 3.2 FeishuImportLog（导入操作日志）

```python
class FeishuImportLog(models.Model):
    """飞书导入操作日志。"""
    doc_token = models.CharField(max_length=128, db_index=True)
    title = models.CharField('文档标题', max_length=300, blank=True)
    status = models.CharField('状态', max_length=16, choices=[('success', '成功'), ('failed', '失败')])
    message = models.TextField('说明', blank=True)
    image_count = models.IntegerField('转存图片数', default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, ...)
    created_at = models.DateTimeField(auto_now_add=True)
```

---

## 四、后端 API 设计（已实现）

### 4.1 API 端点

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/api/admin/feishu/status/` | 应用配置状态 + 文件夹功能开关 | AdminPermission |
| GET | `/api/admin/feishu/documents/` | 共享文件夹文档列表（需配置 FEISHU_FOLDER_TOKEN） | AdminPermission |
| POST | `/api/admin/feishu/import/` | 粘贴链接导入 `{url}`，返回转换后 HTML | AdminPermission |
| GET | `/api/admin/feishu/history/` | 已导入文档记录 | AdminPermission |
| GET | `/api/admin/feishu/logs/` | 导入操作日志 | AdminPermission |

### 4.2 API 详细规格

#### 4.2.1 获取飞书状态

**请求**：
```
GET /api/admin/feishu/status/
```

**响应**：
```json
{
  "configured": true,
  "authorized": true,
  "feishu_user": "张三",
  "expires_at": "2026-08-19T10:30:00Z"
}
```

#### 4.2.2 获取授权 URL

**请求**：
```
GET /api/admin/feishu/authorize/
```

**响应**：
```json
{
  "auth_url": "https://open.feishu.cn/open-apis/authen/v1/authorize?app_id=xxx&redirect_uri=xxx&state=xxx"
}
```

#### 4.2.3 OAuth 回调

**请求**：
```
GET /api/admin/feishu/callback/?code=xxx&state=xxx
```

**响应**：
```json
{
  "success": true,
  "message": "授权成功"
}
```

#### 4.2.4 获取文档列表

**请求**：
```
GET /api/admin/feishu/documents/?folder_token=xxx&page_size=20
```

**响应**：
```json
{
  "documents": [
    {
      "token": "doccnxxxxxxxx",
      "title": "产品发布公告",
      "type": "docx",
      "url": "https://xxx.feishu.cn/docx/xxxxx",
      "created_at": "2026-08-18T10:00:00Z",
      "modified_at": "2026-08-19T09:00:00Z"
    }
  ],
  "has_more": false,
  "page_token": "xxx"
}
```

#### 4.2.5 导入文档

**请求**：
```
POST /api/admin/feishu/import/doccnxxxxxxxx/
```

**响应**：
```json
{
  "success": true,
  "title": "产品发布公告",
  "html": "<h1>产品发布公告</h1><p>尊敬的用户...</p><div style=\"display: flex; gap: 1%;\"><div style=\"flex: 0 0 49%;\"><img src=\"https://cos.xxx/image1.png\"></div><div style=\"flex: 0 0 49%;\"><img src=\"https://cos.xxx/image2.png\"></div></div>",
  "image_count": 5,
  "doc_token": "doccnxxxxxxxx"
}
```

#### 4.2.6 增量同步

**请求**：
```
POST /api/admin/feishu/sync/doccnxxxxxxxx/
```

**响应**：
```json
{
  "success": true,
  "article_id": 123,
  "updated_fields": ["content_html", "updated_at"]
}
```

---

## 五、飞书文档解析器设计

### 5.1 核心类：FeishuDocParser

```python
class FeishuDocParser:
    """飞书文档解析器（Block 树 → UEditorPlus HTML）"""

    # Block 类型常量
    BLOCK_TYPE_PAGE = 1
    BLOCK_TYPE_TEXT = 2
    BLOCK_TYPE_HEADING1 = 3
    BLOCK_TYPE_HEADING2 = 4
    BLOCK_TYPE_HEADING3 = 5
    BLOCK_TYPE_HEADING4 = 6
    BLOCK_TYPE_HEADING5 = 7
    BLOCK_TYPE_HEADING6 = 8
    BLOCK_TYPE_BULLET = 12
    BLOCK_TYPE_ORDERED = 13
    BLOCK_TYPE_CODE = 14
    BLOCK_TYPE_QUOTE = 15
    BLOCK_TYPE_DIVIDER = 22
    BLOCK_TYPE_IMAGE = 27
    BLOCK_TYPE_GRID = 24
    BLOCK_TYPE_GRID_COLUMN = 25
    BLOCK_TYPE_TABLE = 31
    BLOCK_TYPE_CALLOUT = 19

    def __init__(self):
        self.image_map = {}  # token → COS URL 映射
        self.document_id = None
        self.user_token = None

    def parse_document(self, doc_data: dict, doc_token: str, user_token: str) -> dict:
        """
        解析飞书文档，返回 HTML 和元数据

        Args:
            doc_data: 飞书 API 返回的文档数据（包含 blocks 数组）
            doc_token: 文档 token
            user_token: 用户 access_token（用于下载图片）

        Returns:
            {
                'title': '文档标题',
                'html': '<h1>...</h1><p>...</p>',
                'image_count': 5,
            }
        """
        self.document_id = doc_token
        self.user_token = user_token
        blocks = doc_data.get('blocks', [])

        root_block = self._find_root_block(blocks)
        if not root_block:
            return {'title': '', 'html': '', 'image_count': 0}

        html_parts = []
        for child_id in root_block.get('children', []):
            child_block = self._find_block_by_id(blocks, child_id)
            if child_block:
                html = self._parse_block(child_block, blocks)
                if html:
                    html_parts.append(html)

        return {
            'title': self._extract_title(doc_data),
            'html': '\n'.join(html_parts),
            'image_count': len(self.image_map),
        }
```

### 5.2 Block 类型映射表

| 飞书 Block 类型 | block_type | 输出 HTML | 说明 |
|---|---|---|---|
| Page | 1 | 递归解析子块 | 根节点 |
| Text | 2 | `<p>文本</p>` | 普通文本 |
| Heading1 | 3 | `<h1>标题</h1>` | 一级标题 |
| Heading2 | 4 | `<h2>标题</h2>` | 二级标题 |
| Heading3 | 5 | `<h3>标题</h3>` | 三级标题 |
| Heading4-6 | 6-8 | `<h4>`~`<h6>` | 四到六级标题 |
| Bullet | 12 | `<ul><li>文本</li></ul>` | 无序列表 |
| Ordered | 13 | `<ol><li>文本</li></ol>` | 有序列表 |
| Code | 14 | `<pre class="language-xxx"><code>代码</code></pre>` | 代码块 |
| Quote | 15 | `<blockquote>引用</blockquote>` | 引用块 |
| Divider | 22 | `<hr>` | 分割线 |
| Image | 27 | `<img src="COS_URL">` | 图片（需转存 COS） |
| Grid | 24 | `<div style="display: flex">分栏容器</div>` | 分栏布局 |
| Grid Column | 25 | `<div style="flex: 0 0 X%">列</div>` | 分栏列 |
| Table | 31 | `<table>表格</table>` | 表格 |
| Callout | 19 | `<div class="feishu-callout">高亮块</div>` | 高亮块 |

### 5.3 并排图片处理（Grid Block）

**飞书结构**：
```
grid (block_type=24)
├── grid_column (width_ratio=50)
│   └── image (type=27)
└── grid_column (width_ratio=50)
    └── image (type=27)
```

**解析逻辑**：

```python
def _parse_grid(self, block, blocks):
    """解析分栏布局（多图同行）"""
    grid_prop = block.get('grid', {})
    children_ids = block.get('children', [])

    columns = []
    column_widths = []
    for child_id in children_ids:
        child_block = self._find_block_by_id(blocks, child_id)
        if child_block:
            column_html = self._parse_grid_column(child_block, blocks)
            columns.append(column_html)

            # 获取列宽比例
            column_prop = child_block.get('grid_column', {})
            width_ratio = column_prop.get('width_ratio', 50)
            column_widths.append(width_ratio)

    # 根据列数生成不同布局
    if len(columns) == 2:
        return self._create_two_column_layout(columns, column_widths)
    elif len(columns) == 3:
        return self._create_three_column_layout(columns, column_widths)
    elif len(columns) > 3:
        return self._create_multi_column_layout(columns, column_widths)
    return ''

def _create_two_column_layout(self, columns, width_ratios):
    """创建双栏布局"""
    if width_ratios and len(width_ratios) >= 2:
        ratio1, ratio2 = width_ratios[0], width_ratios[1]
        total = ratio1 + ratio2
        width1 = round((ratio1 / total) * 98, 1)  # 留 2% gap
        width2 = round((ratio2 / total) * 98, 1)
    else:
        width1 = width2 = 49.0

    return f'''<div style="display: flex; flex-wrap: wrap; gap: 1%; justify-content: center;">
<div style="flex: 0 0 {width1}%; text-align: center;">{columns[0]}</div>
<div style="flex: 0 0 {width2}%; text-align: center;">{columns[1]}</div>
</div>'''

def _parse_image(self, block, blocks):
    """解析图片块"""
    image_prop = block.get('image', {})
    token = image_prop.get('temp_file_token') or image_prop.get('file_token')

    if not token:
        return '[图片]'

    # 转存到 COS
    cos_url = self._upload_image_to_cos(token)
    self.image_map[token] = cos_url

    # 检测是否在 Grid 内
    parent_id = block.get('parent_id', '')
    parent_block = self._find_block_by_id(blocks, parent_id) if parent_id else None
    in_grid = parent_block and parent_block.get('block_type') in [self.BLOCK_TYPE_GRID, self.BLOCK_TYPE_GRID_COLUMN]

    if in_grid:
        # Grid 内图片宽度由容器控制
        return f'<img src="{cos_url}" style="width: 100%; height: auto; display: block;">'
    else:
        # 独立图片，限制最大宽度
        return f'<img src="{cos_url}" style="max-width: 100%; height: auto; display: block; margin: 0 auto;">'
```

### 5.4 图片转存 COS

```python
def _upload_image_to_cos(self, token: str) -> str:
    """下载飞书图片并转存到 COS"""
    try:
        # 调用飞书 API 下载图片
        image_data = feishu_doc_api.download_image(token, self.user_token)

        # 压缩大图（可选）
        if len(image_data) > 4 * 1024 * 1024:
            image_data = self._compress_image(image_data, 4 * 1024 * 1024)

        # 上传到 COS
        from apps.common import cos
        ext = '.png'  # 飞书图片默认 png
        key = cos.build_object_key('images', ext)
        url = cos.upload_bytes(key, image_data, 'image/png')

        return url
    except Exception as e:
        logger.error(f'图片转存失败: {e}')
        return f'feishu_image://{token}'  # 占位符
```

---

## 六、前端集成设计

### 6.1 UEditorPlus 工具栏按钮位置

**当前工具栏配置**（`UEditor.vue` 第 32-39 行）：
```javascript
toolbars: [[
  'fullscreen', 'source', '|', 'undo', 'redo', '|', 'bold', 'italic', 'underline', 'fontborder',
  'strikethrough', '|', 'forecolor', 'backcolor', '|', 'insertorderedlist', 'insertunorderedlist',
  '|', 'justifyleft', 'justifycenter', 'justifyright', 'justifyjustify', '|', 'link', 'unlink', '|',
  'insertimage', 'emotion', 'scrawl', '|', 'insertvideo', 'insertaudio', 'attachment', '|',
  'horizontal', 'date', 'time', 'spechars', '|', 'inserttable', 'deletetable', '|',
  'xiumi', '|', 'template', 'background', 'formula', '|', 'print', 'preview'
]]
```

**修改后配置**（在 `xiumi` 后添加 `feishuimport`）：
```javascript
toolbars: [[
  'fullscreen', 'source', '|', 'undo', 'redo', '|', 'bold', 'italic', 'underline', 'fontborder',
  'strikethrough', '|', 'forecolor', 'backcolor', '|', 'insertorderedlist', 'insertunorderedlist',
  '|', 'justifyleft', 'justifycenter', 'justifyright', 'justifyjustify', '|', 'link', 'unlink', '|',
  'insertimage', 'emotion', 'scrawl', '|', 'insertvideo', 'insertaudio', 'attachment', '|',
  'horizontal', 'date', 'time', 'spechars', '|', 'inserttable', 'deletetable', '|',
  'xiumi', 'feishuimport', '|', 'template', 'background', 'formula', '|', 'print', 'preview'
]]
```

### 6.2 飞书导入对话框

**文件位置**：`web/public/UEditorPlus/dialogs/feishu-import/feishu-import.html`

**界面结构**：
```
┌─────────────────────────────────────────┐
│  飞书文档导入                           │
├─────────────────────────────────────────┤
│  [授权状态] 已授权：张三  [切换账号]    │
│                                         │
│  文档列表：                             │
│  ┌─────────────────────────────────┐   │
│  │ 📄 产品发布公告                  │   │
│  │    修改时间：2026-08-19 09:00   │   │
│  │    [导入] [预览]                │   │
│  ├─────────────────────────────────┤   │
│  │ 📄 技术文档 v2                   │   │
│  │    修改时间：2026-08-18 15:30   │   │
│  │    [导入] [预览]                │   │
│  └─────────────────────────────────┘   │
│                                         │
│  [刷新列表]  [关闭]                     │
└─────────────────────────────────────────┘
```

### 6.3 导入流程

```
1. 用户点击工具栏"飞书导入"按钮
   ↓
2. 弹出对话框，检查飞书授权状态
   ↓
3. 未授权 → 跳转飞书 OAuth 页面 → 回调后刷新状态
   ↓
4. 已授权 → 拉取飞书文档列表
   ↓
5. 用户选择文档，点击"导入"
   ↓
6. 后端解析文档，返回 HTML
   ↓
7. 对话框显示预览，用户确认
   ↓
8. 将 HTML 注入 UEditor 编辑器（editor.setContent(html)）
   ↓
9. 用户在编辑器中微调，保存文章
```

### 6.4 对话框 JavaScript 逻辑

**文件位置**：`web/public/UEditorPlus/dialogs/feishu-import/feishu-import.js`

```javascript
// 核心逻辑伪代码
async function checkFeishuStatus() {
  const res = await fetch('/api/admin/feishu/status/')
  const data = await res.json()
  if (!data.authorized) {
    showAuthorizeButton()
  } else {
    showDocumentList()
  }
}

async function loadDocumentList() {
  const res = await fetch('/api/admin/feishu/documents/')
  const data = await res.json()
  renderDocumentList(data.documents)
}

async function importDocument(docToken) {
  const res = await fetch(`/api/admin/feishu/import/${docToken}/`, {
    method: 'POST',
    headers: { 'X-CSRFToken': getCsrfToken() }
  })
  const data = await res.json()
  if (data.success) {
    // 注入到 UEditor
    editor.execCommand('insertHtml', data.html)
    dialog.close()
  }
}
```

---

## 七、关键实现细节

### 7.1 飞书 OAuth 流程

**后端配置**（`settings/prod.py`）：
```python
FEISHU_APP_ID = os.environ.get('FEISHU_APP_ID', '')
FEISHU_APP_SECRET = os.environ.get('FEISHU_APP_SECRET', '')
FEISHU_REDIRECT_URI = 'https://cloverweb.com/api/admin/feishu/callback/'
```

**授权 URL 生成**（`feishu_views.py`）：
```python
def get_authorize_url(request):
    state = f'user_{request.user.id}'
    auth_url = (
        f'https://open.feishu.cn/open-apis/authen/v1/authorize'
        f'?app_id={settings.FEISHU_APP_ID}'
        f'&redirect_uri={settings.FEISHU_REDIRECT_URI}'
        f'&state={state}'
        f'&response_type=code'
    )
    return {'auth_url': auth_url}
```

**回调处理**（`feishu_views.py`）：
```python
def oauth_callback(request):
    code = request.GET.get('code')
    state = request.GET.get('state')

    # 用 code 换 user_access_token
    token_data = feishu_auth.get_user_access_token(code)

    # 获取用户信息
    user_info = feishu_auth.get_user_info(token_data['access_token'])

    # 持久化 token
    FeishuToken.objects.update_or_create(
        user=request.user,
        defaults={
            'access_token': token_data['access_token'],
            'refresh_token': token_data.get('refresh_token', ''),
            'expires_at': timezone.now() + timedelta(seconds=token_data.get('expires_in', 7200)),
            'feishu_user_id': token_data.get('user_id', ''),
            'feishu_open_id': token_data.get('open_id', ''),
            'feishu_name': user_info.get('name', ''),
        }
    )

    return {'success': True, 'message': '授权成功'}
```

### 7.2 Token 刷新机制

```python
def get_valid_token(user):
    """获取有效的 user_access_token（过期则自动刷新）"""
    try:
        feishu_token = FeishuToken.objects.get(user=user)
    except FeishuToken.DoesNotExist:
        return None

    # 检查是否过期（提前 5 分钟刷新）
    if feishu_token.expires_at and timezone.now() >= feishu_token.expires_at - timedelta(minutes=5):
        # 调用飞书 API 刷新 token
        new_token = feishu_auth.refresh_token(feishu_token.refresh_token)
        feishu_token.access_token = new_token['access_token']
        feishu_token.refresh_token = new_token.get('refresh_token', feishu_token.refresh_token)
        feishu_token.expires_at = timezone.now() + timedelta(seconds=new_token.get('expires_in', 7200))
        feishu_token.save()

    return feishu_token.access_token
```

### 7.3 增量同步逻辑

```python
def sync_document(request, doc_token):
    """增量同步飞书文档"""
    try:
        feishu_doc = FeishuDocument.objects.get(doc_token=doc_token)
    except FeishuDocument.DoesNotExist:
        return {'success': False, 'message': '文档未导入过'}

    # 获取最新文档数据
    doc_data = feishu_doc_api.get_document_content(doc_token, user_token)

    # 解析为 HTML
    parser = FeishuDocParser()
    result = parser.parse_document(doc_data, doc_token, user_token)

    # 更新关联文章
    if feishu_doc.article:
        article = feishu_doc.article
        article.content_html = result['html']
        article.title = result['title']
        article.save()

        # 更新同步时间
        feishu_doc.last_sync_at = timezone.now()
        feishu_doc.save()

        return {'success': True, 'article_id': article.id}
    else:
        return {'success': False, 'message': '未关联文章'}
```

---

## 八、部署与配置

### 8.1 环境变量

```bash
# .env
FEISHU_APP_ID=cli_xxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
FEISHU_REDIRECT_URI=https://cloverweb.com/api/admin/feishu/callback/
```

### 8.2 飞书应用权限

在飞书开放平台配置以下权限：
- `docx:document:readonly` — 读取文档内容
- `drive:drive:readonly` — 读取云空间文件列表
- `auth:user_access_token` — 获取用户 access_token

### 8.3 数据库迁移

```bash
python manage.py makemigrations content
python manage.py migrate
```

---

## 九、测试计划

### 9.1 单元测试

- [ ] 飞书 Block 解析器（各类型 Block → HTML）
- [ ] 并排图片处理（Grid Block）
- [ ] 图片转存 COS
- [ ] Token 刷新逻辑

### 9.2 集成测试

- [ ] OAuth 授权流程
- [ ] 文档列表拉取
- [ ] 文档导入 → UEditor 注入
- [ ] 增量同步

### 9.3 端到端测试

- [ ] 完整导入流程（从点击按钮到保存文章）
- [ ] 复杂文档（图文混排、表格、分栏）
- [ ] 大图压缩
- [ ] 网络异常处理

---

## 十、实施计划

### Phase 1：基础导入（MVP）— 3 天

**目标**：实现单文档导入，支持基础 Block 类型

**任务**：
1. 新增数据模型（FeishuDocument, FeishuImportLog, FeishuToken）
2. 实现飞书 API 封装（文档列表、文档内容、图片下载）
3. 实现基础解析器（text, heading, image, list, code）
4. 实现导入 API 端点
5. 前端对话框（文档列表 + 导入按钮）
6. UEditor 工具栏集成

### Phase 2：复杂格式支持 — 2 天

**目标**：支持分栏布局、表格、高亮块

**任务**：
1. Grid Block 解析（多图并排）
2. Table Block 解析
3. Callout Block 解析
4. 图片压缩优化

### Phase 3：增量同步与日志 — 2 天

**目标**：支持文档更新、导入历史

**任务**：
1. 增量同步 API
2. 导入日志页面
3. Token 自动刷新

### Phase 4：优化与测试 — 3 天

**目标**：性能优化、异常处理、测试覆盖

**任务**：
1. 大图压缩与裁剪
2. 网络异常重试
3. 单元测试 & 集成测试
4. 文档编写

---

## 十一、风险与应对

| 风险 | 影响 | 应对措施 |
|---|---|---|
| 飞书图片防盗链 | 导入后图片无法显示 | 导入时立即转存 COS |
| Token 过期 | 导入中断 | 自动刷新机制 |
| 大文档解析慢 | 用户体验差 | 异步解析 + 进度提示 |
| UEditor 兼容性问题 | 分栏布局显示异常 | 充分测试，降级为单列 |

---

## 十二、附录

### 12.1 飞书 Block 类型参考

详见：`main/blog_system/飞书文档说明.md`

### 12.2 旧系统解析器参考

详见：`main/blog_system/feishu_parser.py`

### 12.3 UEditorPlus 工具栏配置

详见：`web/src/components/content-editor/UEditor.vue`

---

**文档版本**：v1.0
**创建时间**：2026-08-19
**作者**：cloverweb 开发团队
