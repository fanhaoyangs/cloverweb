"""飞书文档 Block 树 → UEditorPlus HTML 转换器。

沿用旧系统（main/blog_system/feishu_parser.py）的布局策略：
- Grid（block_type=24）分栏 → flex 布局，按 width_ratio 分配列宽（留 2% gap）
- Grid 内图片 width:100%（宽度由容器控制），独立图片 max-width:100% 居中
- 图片下载后转存腾讯云 COS（apps.common.cos），HTML 中引用 COS URL

Block 类型（docx v1）：
  1 Page | 2 Text | 3-11 Heading1-9 | 12 Bullet | 13 Ordered | 14 Code | 15 Quote
  17 Todo | 19 Callout | 22 Divider | 23 File | 24 Grid | 25 GridColumn
  26 Iframe | 27 Image | 31 Table | 32 TableCell | 34 QuoteContainer
"""
import html
import logging

from apps.common import cos

from . import feishu_api

logger = logging.getLogger(__name__)

# Block 类型常量
PAGE = 1
TEXT = 2
HEADING1 = 3
HEADING9 = 11
BULLET = 12
ORDERED = 13
CODE = 14
QUOTE = 15
TODO = 17
CALLOUT = 19
DIVIDER = 22
FILE = 23
GRID = 24
GRID_COLUMN = 25
IFRAME = 26
IMAGE = 27
TABLE = 31
TABLE_CELL = 32
QUOTE_CONTAINER = 34

# 飞书 code block language → HTML class
CODE_LANG_MAP = {
    'PlainText': '', 'Code': '', 'Java': 'java', 'Python': 'python', 'Go': 'go',
    'Sql': 'sql', 'Bash': 'bash', 'Shell': 'bash', 'C': 'c', 'Cpp': 'cpp',
    'JavaScript': 'javascript', 'TypeScript': 'typescript', 'Json': 'json',
    'Html': 'html', 'Css': 'css', 'Php': 'php', 'Ruby': 'ruby', 'Rust': 'rust',
    'Swift': 'swift', 'Kotlin': 'kotlin', 'Markdown': 'markdown', 'Yaml': 'yaml',
}


def esc(text: str) -> str:
    return html.escape(text or '', quote=False)


class FeishuDocParser:
    """飞书文档解析器。用法：parser.parse(blocks, doc_token) → {'title', 'html', 'image_count'}"""

    def __init__(self, user_token: str = ''):
        self.blocks_by_id = {}
        self.image_count = 0
        self.image_failed = 0
        self.user_token = user_token

    # ---- 对外入口 ----

    def parse(self, blocks: list, title: str = '') -> dict:
        self.blocks_by_id = {b['block_id']: b for b in blocks}
        root = None
        for b in blocks:
            if b.get('block_type') == PAGE:
                root = b
                break
        if not root:
            return {'title': title, 'html': '', 'image_count': 0}

        html_body = self._parse_children_sequence(root.get('children', []))
        return {
            'title': title,
            'html': html_body,
            'image_count': self.image_count,
            'image_failed': self.image_failed,
        }

    # ---- Block 分发 ----

    def _block(self, block_id):
        return self.blocks_by_id.get(block_id)

    def _parse_block(self, block_id) -> str:
        block = self._block(block_id)
        if not block:
            return ''
        btype = block.get('block_type')

        if btype == TEXT or (HEADING1 <= btype <= HEADING9):
            return self._parse_text_block(block)
        if btype in (BULLET, ORDERED):
            return ''  # 列表在外层合并处理（_parse_children_sequence）
        if btype == CODE:
            return self._parse_code(block)
        if btype in (QUOTE, QUOTE_CONTAINER):
            return self._parse_quote(block)
        if btype == TODO:
            return self._parse_todo(block)
        if btype == CALLOUT:
            return self._parse_callout(block)
        if btype == DIVIDER:
            return '<hr/>'
        if btype == IMAGE:
            return self._parse_image(block, in_grid=False)
        if btype == GRID:
            return self._parse_grid(block)
        if btype == GRID_COLUMN:
            return ''  # 由 _parse_grid 处理
        if btype == TABLE:
            return self._parse_table(block)
        if btype in (FILE, IFRAME):
            return self._parse_file(block)
        # 未支持类型（bitable/sheet/board 等）：跳过并记录
        logger.info('跳过未支持的飞书 Block 类型: %s', btype)
        return ''

    def _parse_children_sequence(self, children_ids: list) -> str:
        """解析子块序列；连续的 bullet / ordered 合并为完整 <ul>/<ol>。"""
        parts = []
        list_items, list_type = [], None

        def flush():
            if list_items:
                tag = 'ul' if list_type == BULLET else 'ol'
                items = ''.join(f'<li>{item}</li>' for item in list_items)
                parts.append(f'<{tag}>{items}</{tag}>')
                list_items.clear()

        for cid in children_ids:
            block = self._block(cid)
            if not block:
                continue
            btype = block.get('block_type')
            if btype in (BULLET, ORDERED):
                if list_type and list_type != btype:
                    flush()
                list_type = btype
                # 列表项内容 = 直接子文本块内联 + 嵌套子列表（保持缩进层级）
                item_inline, item_nested = [], []
                for sub_id in block.get('children', []):
                    sub = self._block(sub_id)
                    if not sub:
                        continue
                    sub_type = sub.get('block_type')
                    if sub_type in (BULLET, ORDERED):
                        item_nested.append(self._parse_children_sequence([sub_id]))
                    elif sub_type == TEXT or HEADING1 <= sub_type <= HEADING9:
                        data = sub.get('text') or {}
                        content = self._inline_elements(data.get('elements', []))
                        if content.strip():
                            item_inline.append(content)
                    elif sub_type == IMAGE:
                        item_nested.append(self._parse_image(sub, in_grid=False))
                list_items.append(' '.join(item_inline) + ''.join(item_nested))
            else:
                flush()
                list_type = None
                parts.append(self._parse_block(cid))
        flush()
        return '\n'.join(p for p in parts if p)

    # ---- 文本类 ----

    def _parse_text_block(self, block) -> str:
        btype = block.get('block_type')
        data = block.get('text') or block.get('heading1') or block.get('heading2') \
            or block.get('heading3') or block.get('heading4') or block.get('heading5') \
            or block.get('heading6') or block.get('heading7') or block.get('heading8') \
            or block.get('heading9') or {}
        content = self._inline_elements(data.get('elements', []))
        if not content.strip():
            return ''
        if btype == TEXT:
            return f'<p>{content}</p>'
        level = min(btype - HEADING1 + 1, 4)  # UEditorPlus 常用 h1-h4
        return f'<h{level}>{content}</h{level}>'

    def _inline_children(self, children_ids: list) -> str:
        """子块的内联文本拼接（用于列表项等容器场景）。"""
        parts = []
        for cid in children_ids:
            block = self._block(cid)
            if not block:
                continue
            btype = block.get('block_type')
            if btype == TEXT or (HEADING1 <= btype <= HEADING9):
                data = block.get('text') or {}
                parts.append(self._inline_elements(data.get('elements', [])))
            elif btype == IMAGE:
                parts.append(self._parse_image(block, in_grid=False))
        return ' '.join(p for p in parts if p)

    def _inline_elements(self, elements: list) -> str:
        """text_run 等元素 → 带样式的内联 HTML。"""
        parts = []
        for el in elements:
            run = el.get('text_run')
            if not run:
                # mention_doc / mention_user 等：MVP 忽略
                continue
            text = esc(run.get('content', ''))
            style = run.get('text_element_style') or {}
            if style.get('inline_code'):
                text = f'<code>{text}</code>'
            link = (style.get('link') or {}).get('url')
            if link:
                text = f'<a href="{esc(link)}" target="_blank" rel="noopener">{text}</a>'
            if style.get('strikethrough'):
                text = f'<s>{text}</s>'
            if style.get('underline'):
                text = f'<u>{text}</u>'
            if style.get('italic'):
                text = f'<em>{text}</em>'
            if style.get('bold'):
                text = f'<strong>{text}</strong>'
            parts.append(text)
        return ''.join(parts)

    # ---- 结构类 ----

    def _parse_code(self, block) -> str:
        code = block.get('code') or {}
        lines = []
        for el in code.get('elements', []):
            run = el.get('text_run')
            if run:
                lines.append(run.get('content', ''))
        lang = CODE_LANG_MAP.get(code.get('style', {}).get('language', ''), '')
        cls = f' class="language-{lang}"' if lang else ''
        return f'<pre{cls}><code>{esc("".join(lines))}</code></pre>'

    def _parse_quote(self, block) -> str:
        inner = self._parse_children_sequence(block.get('children', []))
        if not inner.strip():
            return ''
        # 去掉内部段落标签，保持 blockquote 内为纯段落流
        return f'<blockquote>{inner}</blockquote>'

    def _parse_todo(self, block) -> str:
        todo = block.get('todo') or {}
        checked = todo.get('done', False)
        box = '☑' if checked else '☐'
        inner = self._inline_children(block.get('children', []))
        return f'<p><span style="margin-right: 6px;">{box}</span>{inner}</p>'

    def _parse_callout(self, block) -> str:
        callout = block.get('callout') or {}
        emoji = ''
        emoji_data = callout.get('emoji')
        if isinstance(emoji_data, dict):
            emoji = esc(emoji_data.get('emoji_id', ''))
        inner = self._parse_children_sequence(block.get('children', []))
        if not inner.strip():
            return ''
        emoji_prefix = f'<span style="margin-right: 6px;">{emoji}</span>' if emoji else ''
        return (
            '<div style="border-left: 4px solid #3370ff; background: #f5f7fa; '
            'padding: 10px 14px; margin: 10px 0; border-radius: 4px;">'
            f'{emoji_prefix}{inner}</div>'
        )

    def _parse_file(self, block) -> str:
        btype = block.get('block_type')
        if btype == FILE:
            token = (block.get('file') or {}).get('token', '')
            return f'<p>[附件: {esc(token)}]</p>'
        iframe = block.get('iframe') or {}
        url = iframe.get('component') or {}
        return f'<p><a href="{esc(url.get("url", ""))}" target="_blank" rel="noopener">嵌入内容</a></p>'

    # ---- 图片与分栏（核心） ----

    def _parse_image(self, block, in_grid: bool) -> str:
        image = block.get('image') or {}
        token = image.get('token') or image.get('temp_file_token') or ''
        if not token:
            return ''

        cos_url = self._upload_image_to_cos(token)
        if not cos_url:
            self.image_failed += 1
            return '<p style="color: #999;">[图片转存失败]</p>'
        self.image_count += 1

        if in_grid:
            # 分栏内：宽度由 flex 容器控制
            return f'<img src="{cos_url}" style="width: 100%; height: auto; display: block;" alt=""/>'
        # 独立图片：居中，不超出正文宽度
        return (f'<img src="{cos_url}" '
                'style="max-width: 100%; height: auto; display: block; margin: 0 auto;" alt=""/>')

    def _upload_image_to_cos(self, file_token: str) -> str:
        """下载飞书图片并转存 COS，返回 CDN URL；失败返回 ''。"""
        try:
            data = feishu_api.download_image(file_token, self.user_token)
            key = cos.build_object_key('images', '.png')  # 飞书 medias 下载无扩展名，按 png 存储
            return cos.upload_bytes(key, data, 'image/png')
        except Exception:  # noqa: BLE001
            logger.warning('飞书图片转存 COS 失败: %s', file_token, exc_info=True)
            return ''

    def _parse_grid(self, block) -> str:
        """Grid 分栏布局（多图并排核心逻辑，沿用旧系统策略）。"""
        children_ids = [cid for cid in block.get('children', [])]
        columns, width_ratios = [], []
        for cid in children_ids:
            col_block = self._block(cid)
            if not col_block or col_block.get('block_type') != GRID_COLUMN:
                continue
            columns.append(self._parse_grid_column(col_block))
            ratio = (col_block.get('grid_column') or {}).get('width_ratio', 0) or 0
            width_ratios.append(ratio)

        if not columns:
            return ''
        if len(columns) == 1:
            return columns[0]

        if not any(width_ratios):  # 比例缺失时均分
            width_ratios = [1] * len(columns)
        total = sum(width_ratios)
        widths = [round(r / total * 98, 1) for r in width_ratios]  # 留 2% 间隙
        widths[-1] = round(98 - sum(w for w in widths[:-1]), 1)  # 修正取整误差

        cols_html = ''.join(
            f'<div style="flex: 0 0 {w}%; min-width: 0; text-align: center;">{c}</div>'
            for w, c in zip(widths, columns)
        )
        return (
            '<div style="display: flex; flex-wrap: wrap; gap: 1%; justify-content: center; '
            f'margin: 10px 0;">{cols_html}</div>'
        )

    def _parse_grid_column(self, col_block) -> str:
        """分栏列内容：子块纵向排列（图片等块级元素）。"""
        parts = []
        for cid in col_block.get('children', []):
            block = self._block(cid)
            if not block:
                continue
            btype = block.get('block_type')
            if btype == IMAGE:
                parts.append(self._parse_image(block, in_grid=True))
            elif TEXT <= btype <= HEADING9:  # 文本 / 标题块
                data = block.get('text') or {}
                content = self._inline_elements(data.get('elements', []))
                if content.strip():
                    parts.append(f'<p>{content}</p>')
            elif btype == GRID:
                parts.append(self._parse_grid(block))  # 嵌套分栏递归
            else:
                parts.append(self._parse_block(cid))
        return ''.join(p for p in parts if p)

    # ---- 表格 ----

    def _parse_table(self, block) -> str:
        table = block.get('table') or {}
        prop = block.get('property', {}).get('table', {})
        rows, cols = prop.get('row_size', 0), prop.get('col_size', 0)
        cell_ids = table.get('cells', [])
        if not rows or not cols or len(cell_ids) < rows * cols:
            return ''

        trs = []
        for r in range(rows):
            tds = []
            for c in range(cols):
                cell_block = self._block(cell_ids[r * cols + c])
                inner = ''
                if cell_block:
                    inner = self._inline_children(cell_block.get('children', []))
                tds.append('<td>%s</td>' % (inner or '&nbsp;'))
            trs.append('<tr>%s</tr>' % ''.join(tds))
        return f'<table class="feishu-table" style="border-collapse: collapse; width: 100%; margin: 10px 0;">{"".join(trs)}</table>'
