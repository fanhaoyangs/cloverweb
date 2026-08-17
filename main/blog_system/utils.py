"""
辅助函数模块
提供通用的辅助函数，避免循环导入
"""
import re
import bleach
import markdown
from datetime import datetime


def generate_slug(title):
    """生成URL友好的slug"""
    slug = re.sub(r'[^\w\s-]', '', title).strip().lower()
    slug = re.sub(r'[\s_]+', '-', slug)
    return slug


def render_markdown(content):
    """渲染Markdown为HTML"""
    if not content:
        return ''
    
    md = markdown.Markdown(
        extensions=[
            'markdown.extensions.fenced_code',
            'markdown.extensions.tables',
            'markdown.extensions.toc',
            'markdown.extensions.codehilite',
        ],
        extension_configs={
            'markdown.extensions.codehilite': {
                'guess_lang': False
            }
        }
    )
    
    allowed_tags = list(bleach.sanitizer.ALLOWED_TAGS) + [
        'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'strong', 'em', 'u', 'del', 'ins',
        'ul', 'ol', 'li', 'blockquote',
        'pre', 'code',
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'a', 'img',
        'div', 'span',
        'br', 'hr',
        'figure', 'figcaption'
    ]
    allowed_attributes = {
        **bleach.sanitizer.ALLOWED_ATTRIBUTES,
        'img': ['src', 'alt', 'title', 'width', 'height', 'style'],
        'a': ['href', 'title', 'target'],
        'div': ['class', 'style'],
        'span': ['class', 'style'],
        'table': ['class', 'style'],
        'td': ['style', 'colspan'],
        'th': ['style', 'colspan'],
        'figure': ['class', 'style'],
        'figcaption': ['class', 'style'],
    }
    
    content = preprocess_layout_syntax(content)
    html = md.convert(content)
    html = bleach.clean(html, tags=allowed_tags, attributes=allowed_attributes)
    
    return html


def preprocess_layout_syntax(content):
    """预处理排版语法"""
    content = re.sub(
        r'\{ *\.center *\}\s*\n*(!\[.*?\]\(.*?\))',
        r'\n<div class="layout-center">\n\1\n</div>\n',
        content
    )
    
    content = re.sub(
        r'\{ *\.left *\}\s*\n*(!\[.*?\]\(.*?\))',
        r'\n<div class="layout-left">\n\1\n</div>\n',
        content
    )
    
    content = re.sub(
        r'\{ *\.right *\}\s*\n*(!\[.*?\]\(.*?\))',
        r'\n<div class="layout-right">\n\1\n</div>\n',
        content
    )
    
    def replace_caption(match):
        image_part = match.group(1)
        caption = match.group(2)
        return f'<figure class="image-container">{image_part}<figcaption class="image-caption">{caption}</figcaption></figure>'
    
    content = re.sub(
        r'(!\[.*?\]\(.*?\))\s*\{ *\.caption +["\'](.+?)["\'] *\}',
        replace_caption,
        content
    )
    
    content = re.sub(
        r'\{ *\.two-columns *\}\s*\n((?:!\[.*?\]\(.*?\)\s*\n?)+)',
        lambda m: '<div class="two-columns">' + re.sub(r'\s*\n\s*', ' ', m.group(1)) + '</div>\n',
        content
    )
    
    content = re.sub(
        r'\{ *\.three-columns *\}\s*\n((?:!\[.*?\]\(.*?\)\s*\n?)+)',
        lambda m: '<div class="three-columns">' + re.sub(r'\s*\n\s*', ' ', m.group(1)) + '</div>\n',
        content
    )
    
    return content


def create_excerpt(content, length=200):
    """创建文章摘要"""
    text = re.sub(r'[#*_`~\[\]]', '', content)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'\1', text)
    text = text.strip()
    
    if len(text) > length:
        text = text[:length].strip() + '...'
    
    return text
