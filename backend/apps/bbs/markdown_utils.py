"""BBS Markdown 渲染 + XSS 消毒（服务端单一可信源）。

前端只提交 content_md；HTML 由服务端用 python-markdown 渲染后经 bleach
白名单消毒落库，展示端直接 v-html 无注入风险。
"""
import re

import bleach
import markdown as markdown_lib

# 允许的标签白名单（无 script/iframe/style/事件属性）
ALLOWED_TAGS = [
    'a', 'abbr', 'b', 'blockquote', 'br', 'code', 'del', 'em',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img', 'ins',
    'kbd', 'li', 'ol', 'p', 'pre', 's', 'strong', 'sub', 'sup',
    'table', 'tbody', 'td', 'th', 'thead', 'tr', 'u', 'ul',
]
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],
    'img': ['src', 'alt', 'title', 'width', 'height'],
    'abbr': ['title'],
}
ALLOWED_PROTOCOLS = ['http', 'https']

_MD = markdown_lib.Markdown(extensions=['fenced_code', 'tables', 'nl2br', 'sane_lists'])


def md_to_safe_html(md_text: str) -> str:
    """Markdown -> 白名单消毒后的 HTML。"""
    if not md_text:
        return ''
    _MD.reset()
    html = _MD.convert(md_text)
    return bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )


_MD_TOKEN_RE = re.compile(
    r'!\[[^\]]*\]\([^)]*\)'        # 图片
    r'|\[[^\]]*\]\([^)]*\)'        # 链接
    r'|`{1,3}[^`]*`{1,3}'          # 行内/围栏代码
    r'|[*_~>#+\-|]+',              # 强调/引用/标题/列表符号
)


def md_to_excerpt(md_text: str, limit: int = 120) -> str:
    """从 Markdown 提取纯文本摘要（去语法标记，折叠空白）。"""
    text = _MD_TOKEN_RE.sub('', md_text or '')
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:limit]
