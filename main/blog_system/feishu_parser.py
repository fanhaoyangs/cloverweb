"""
飞书文档解析模块
将飞书文档格式转换为Markdown格式
支持多图同行、图文块同行、图片备注等特殊格式
"""
import re
import os
import tempfile
import logging
from datetime import datetime
from feishu_api import feishu_doc_api
from cos_utils import get_uploader

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler('logs/feishu_import.log', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)


class FeishuDocParser:
    """飞书文档解析器"""
    
    BLOCK_TYPE_PAGE = 1
    BLOCK_TYPE_TEXT = 2
    BLOCK_TYPE_HEADING1 = 3
    BLOCK_TYPE_HEADING2 = 4
    BLOCK_TYPE_HEADING3 = 5
    BLOCK_TYPE_HEADING4 = 6
    BLOCK_TYPE_HEADING5 = 7
    BLOCK_TYPE_HEADING6 = 8
    BLOCK_TYPE_BULLET = 9
    BLOCK_TYPE_ORDERED = 10
    BLOCK_TYPE_CODE = 11
    BLOCK_TYPE_QUOTE = 12
    BLOCK_TYPE_EQUATION = 13
    BLOCK_TYPE_DIVIDER = 14
    BLOCK_TYPE_TABLE_OLD = 15
    BLOCK_TYPE_CALLOUT = 16
    BLOCK_TYPE_CHAT_CARD = 17
    BLOCK_TYPE_DIAGRAM = 18
    BLOCK_TYPE_FILE = 19
    BLOCK_TYPE_IFRAME = 20
    BLOCK_TYPE_GRID = 24
    BLOCK_TYPE_GRID_COLUMN = 25
    BLOCK_TYPE_IFRAME = 26
    BLOCK_TYPE_IMAGE = 27
    BLOCK_TYPE_ISV = 28
    BLOCK_TYPE_MINDNOTE = 29
    BLOCK_TYPE_SHEET = 30
    BLOCK_TYPE_TABLE = 31
    BLOCK_TYPE_TABLE_CELL = 32
    
    def __init__(self):
        self.image_uploader = get_uploader()
        self.image_map = {}
        self.document_id = None
        self.user_token = None
        self.sheets_config = {}
    
    def get_sheets_info(self, doc_data, doc_token, user_token=None):
        """预解析文档，获取电子表格信息（不解析内容）"""
        self.document_id = doc_token
        self.user_token = user_token
        blocks = doc_data.get('blocks', [])
        
        if not blocks:
            return []
        
        sheets_info = []
        
        # 找出所有 sheet block
        for block in blocks:
            if block.get('block_type') == 30:  # sheet block
                sheet_prop = block.get('sheet', {})
                token = sheet_prop.get('token', '')
                
                if not token:
                    continue
                
                # 提取 spreadsheet_token
                if '_' in token:
                    spreadsheet_token = token.split('_')[0]
                else:
                    spreadsheet_token = token
                
                try:
                    # 获取工作表列表
                    sheets_data = feishu_doc_api.get_sheet_content(spreadsheet_token, user_token)
                    
                    for i, sheet in enumerate(sheets_data):
                        sheet_title = sheet.get('title', f'表格{i+1}')
                        sheet_values = sheet.get('data', [])
                        column_count = len(sheet_values[0]) if sheet_values and len(sheet_values) > 0 else 0
                        row_count = len(sheet_values) if sheet_values else 0
                        
                        # 跳过空表格
                        if row_count == 0:
                            continue
                        
                        # 获取预览内容（第一行前3个单元格）
                        preview = ''
                        if sheet_values and len(sheet_values) > 0:
                            first_row = sheet_values[0]
                            preview_cells = []
                            for cell in first_row[:3]:
                                cell_text = self._extract_cell_text(cell)
                                if cell_text:
                                    preview_cells.append(cell_text[:20])
                            preview = ' | '.join(preview_cells)
                            if len(preview) > 60:
                                preview = preview[:60] + '...'
                        
                        sheets_info.append({
                            'index': len(sheets_info),
                            'title': sheet_title,
                            'column_count': column_count,
                            'row_count': row_count,
                            'preview': preview or '（空表格）'
                        })
                except Exception as e:
                    logger.warning(f"获取表格信息失败: {e}")
                    sheets_info.append({
                        'index': len(sheets_info),
                        'title': '表格',
                        'column_count': 0,
                        'row_count': 0,
                        'preview': '（无法获取）'
                    })
        
        return sheets_info
    
    def parse_document(self, doc_data, doc_token, user_token=None):
        """解析飞书文档"""
        self.document_id = doc_token  # 存储 document_id
        self.user_token = user_token  # 存储 user_token
        blocks = doc_data.get('blocks', [])
        
        if not blocks:
            logger.warning(f"No blocks found in doc_data. Keys: {list(doc_data.keys())}")
            return ''
        
        logger.info(f"Found {len(blocks)} blocks")
        
        # 打印所有 block 的类型和键名
        for i, block in enumerate(blocks[:20]):
            block_type = block.get('block_type')
            block_keys = list(block.keys())
            logger.debug(f"Block {i}: type={block_type}, keys={block_keys}")
        
        root_block = self._find_root_block(blocks)
        if not root_block:
            logger.warning(f"No root block found. Block types: {[b.get('block_type') for b in blocks[:10]]}")
            return ''
        
        logger.info(f"Root block found: {root_block.get('block_type')}, block_id: {root_block.get('block_id')}")
        
        children_ids = root_block.get('children', [])
        logger.info(f"Root has {len(children_ids)} children: {children_ids[:5]}...")
        
        if not children_ids:
            logger.warning("Root block has no children, trying to parse all non-page blocks")
            for block in blocks:
                if block.get('block_type') != self.BLOCK_TYPE_PAGE:
                    parsed = self._parse_block(block, blocks)
                    if parsed:
                        logger.info(f"Parsed block {block.get('block_type')}: {parsed[:100]}...")
                        return parsed
            return ''
        
        markdown_lines = []
        
        for child_id in children_ids:
            child_block = self._find_block_by_id(blocks, child_id)
            if child_block:
                parsed = self._parse_block(child_block, blocks)
                if parsed:
                    markdown_lines.append(parsed)
                    logger.debug(f"Parsed child {child_id}: {parsed[:50]}...")
        
        result = '\n\n'.join(markdown_lines)
        logger.info(f"Final result length: {len(result)} chars")
        return result
    
    def _find_root_block(self, blocks):
        """找到根块"""
        for block in blocks:
            if block.get('block_type') == self.BLOCK_TYPE_PAGE:
                return block
        return None
    
    def _find_block_by_id(self, blocks, block_id):
        """通过ID找到块"""
        for block in blocks:
            if block.get('block_id') == block_id:
                return block
        return None
    
    def _parse_block(self, block, blocks):
        """解析单个块"""
        block_type = block.get('block_type')
        
        parser_map = {
            self.BLOCK_TYPE_PAGE: self._parse_page,
            self.BLOCK_TYPE_TEXT: self._parse_text,
            self.BLOCK_TYPE_HEADING1: self._parse_heading1,
            self.BLOCK_TYPE_HEADING2: self._parse_heading2,
            self.BLOCK_TYPE_HEADING3: self._parse_heading3,
            self.BLOCK_TYPE_HEADING4: self._parse_heading4,
            self.BLOCK_TYPE_HEADING5: self._parse_heading5,
            self.BLOCK_TYPE_HEADING6: self._parse_heading6,
            self.BLOCK_TYPE_BULLET: self._parse_bullet,
            self.BLOCK_TYPE_ORDERED: self._parse_ordered,
            self.BLOCK_TYPE_CODE: self._parse_code,
            self.BLOCK_TYPE_QUOTE: self._parse_quote,
            self.BLOCK_TYPE_DIVIDER: self._parse_divider,
            self.BLOCK_TYPE_CALLOUT: self._parse_callout,
            self.BLOCK_TYPE_GRID: self._parse_grid,
            self.BLOCK_TYPE_GRID_COLUMN: self._parse_grid_column,
            self.BLOCK_TYPE_IMAGE: self._parse_image,
            self.BLOCK_TYPE_SHEET: self._parse_sheet,
            self.BLOCK_TYPE_TABLE: self._parse_table,
            self.BLOCK_TYPE_TABLE_CELL: self._parse_table_cell,
        }
        
        parser = parser_map.get(block_type)
        if parser:
            return parser(block, blocks)
        
        logger.debug(f"Unknown block type: {block_type}, trying to extract text or children")
        
        if block.get('children'):
            return self._parse_children(block, blocks)
        
        return self._parse_text(block, blocks)
    
    def _parse_page(self, block, blocks):
        """解析页面块"""
        children_ids = block.get('children', [])
        lines = []
        
        for child_id in children_ids:
            child_block = self._find_block_by_id(blocks, child_id)
            if child_block:
                parsed = self._parse_block(child_block, blocks)
                if parsed:
                    lines.append(parsed)
        
        return '\n\n'.join(lines)
    
    def _parse_text(self, block, blocks):
        """解析文本块"""
        text_prop = block.get('text', {})
        elements = text_prop.get('elements', [])
        
        text_parts = []
        for elem in elements:
            text_run = elem.get('text_run', {})
            content = text_run.get('content', '')
            
            text_elem = elem.get('text_elem', {})
            style = text_elem.get('text_element_style', {})
            
            if style.get('bold'):
                content = f'**{content}**'
            if style.get('italic'):
                content = f'*{content}*'
            if style.get('underline'):
                content = f'<u>{content}</u>'
            if style.get('strikethrough'):
                content = f'~~{content}~~'
            if style.get('inline_code'):
                content = f'`{content}`'
            
            link = text_elem.get('link', {})
            if link:
                url = link.get('url', '')
                content = f'[{content}]({url})'
            
            text_parts.append(content)
        
        return ''.join(text_parts)
    
    def _parse_heading1(self, block, blocks):
        """解析一级标题"""
        text = self._extract_text(block)
        return f'# {text}'
    
    def _parse_heading2(self, block, blocks):
        """解析二级标题"""
        text = self._extract_text(block)
        return f'## {text}'
    
    def _parse_heading3(self, block, blocks):
        """解析三级标题"""
        text = self._extract_text(block)
        return f'### {text}'
    
    def _parse_heading4(self, block, blocks):
        """解析四级标题"""
        text = self._extract_text(block)
        return f'#### {text}'
    
    def _parse_heading5(self, block, blocks):
        """解析五级标题"""
        text = self._extract_text(block)
        return f'##### {text}'
    
    def _parse_heading6(self, block, blocks):
        """解析六级标题"""
        text = self._extract_text(block)
        return f'###### {text}'
    
    def _parse_bullet(self, block, blocks):
        """解析无序列表"""
        text = self._extract_text(block)
        return f'- {text}'
    
    def _parse_ordered(self, block, blocks):
        """解析有序列表"""
        text = self._extract_text(block)
        return f'1. {text}'
    
    def _parse_code(self, block, blocks):
        """解析代码块"""
        code_prop = block.get('code', {})
        elements = code_prop.get('elements', [])
        
        code_lines = []
        for elem in elements:
            text_run = elem.get('text_run', {})
            code_lines.append(text_run.get('content', ''))
        
        language = code_prop.get('style', {}).get('language', '')
        code_content = '\n'.join(code_lines)
        
        return f'```{language}\n{code_content}\n```'
    
    def _parse_quote(self, block, blocks):
        """解析引用块"""
        text = self._extract_text(block)
        lines = text.split('\n')
        return '\n'.join([f'> {line}' for line in lines])
    
    def _parse_table(self, block, blocks):
        """解析表格"""
        table_prop = block.get('table', {})
        cell_ids = table_prop.get('cells', [])
        rows = table_prop.get('property', {}).get('row_size', 0)
        cols = table_prop.get('property', {}).get('column_size', 0)
        
        logger.info(f"Parsing table: {rows}x{cols}, {len(cell_ids) if cell_ids else 0} cell_ids")
        logger.debug(f"Table cell_ids: {cell_ids[:5] if cell_ids else 'none'}...")
        
        if rows == 0 or cols == 0:
            logger.warning("Table has 0 rows or 0 cols")
            return ''
        
        # 构建表格数据
        table_data = []
        for i in range(rows):
            row_data = []
            for j in range(cols):
                cell_index = i * cols + j
                if cell_index < len(cell_ids):
                    cell_id = cell_ids[cell_index]
                    cell_content = self._get_cell_content_by_id(cell_id, blocks)
                    row_data.append(cell_content)
                else:
                    row_data.append('')
            table_data.append(row_data)
        
        logger.debug(f"Table data: {table_data[:2]}...")
        
        # 生成 HTML 表格
        html_table = ['<table style="border-collapse: collapse; width: 100%;">']
        
        for i, row in enumerate(table_data):
            html_table.append('<tr>')
            for j, cell_content in enumerate(row):
                tag = 'th' if i == 0 else 'td'
                style = 'border: 1px solid #ddd; padding: 8px;'
                if i == 0:
                    style += ' background-color: #f2f2f2; font-weight: bold;'
                html_table.append(f'<{tag} style="{style}">{cell_content}</{tag}>')
            html_table.append('</tr>')
        
        html_table.append('</table>')
        result = '\n'.join(html_table)
        logger.info(f"Table parsed successfully, length: {len(result)} chars")
        return result
    
    def _get_cell_content_by_id(self, cell_id, blocks):
        """通过ID获取单元格内容"""
        cell_block = self._find_block_by_id(blocks, cell_id)
        if not cell_block:
            return ''
        
        # 单元格的子块包含实际内容
        children_ids = cell_block.get('children', [])
        if not children_ids:
            return ''
        
        content_parts = []
        for child_id in children_ids:
            child_block = self._find_block_by_id(blocks, child_id)
            if child_block:
                parsed = self._parse_block(child_block, blocks)
                if parsed:
                    content_parts.append(parsed)
        
        return ' '.join(content_parts)
    
    def _parse_image(self, block, blocks):
        """解析图片块"""
        block_id = block.get('block_id')
        image_prop = block.get('image', {})
        
        logger.debug(f"Image block keys: {list(block.keys())}")
        logger.debug(f"Image prop keys: {list(image_prop.keys())}")
        logger.debug(f"Image prop: {image_prop}")
        
        file_token = image_prop.get('file_token', '')
        temp_file_token = image_prop.get('temp_file_token', '')
        token = file_token or temp_file_token
        
        if not token:
            for key in ['token', 'file_token', 'temp_file_token', 'image_token']:
                if image_prop.get(key):
                    token = image_prop.get(key)
                    logger.debug(f"Found token in {key}: {token[:20]}...")
                    break
        
        if not token:
            logger.warning(f"No token found in image block: {image_prop}")
            return '[图片]'
        
        logger.info(f"Processing image token: {token[:20]}...")
        image_url = self._process_image(token)
        
        align = image_prop.get('align', 1)
        width = image_prop.get('width', 0)
        height = image_prop.get('height', 0)
        caption_obj = image_prop.get('caption', {})
        caption = caption_obj.get('content', '') if isinstance(caption_obj, dict) else ''
        
        logger.debug(f"Image caption: {caption}, width: {width}, height: {height}, align: {align}")
        
        alt_text = caption if caption else '图片'
        
        # 根据 align 设置对齐方式
        if align == 1:
            margin_style = 'margin: 0 auto 0 0;'
        elif align == 3:
            margin_style = 'margin: 0 0 0 auto;'
        else:
            margin_style = 'margin: 0 auto;'
        
        if width and height and width > 0 and height > 0:
            # 限制最大宽度，保持原始比例
            max_display_width = 800
            if width > max_display_width:
                ratio = max_display_width / width
                display_width = max_display_width
                display_height = int(height * ratio)
            else:
                display_width = width
                display_height = height
            
            # 飞书 API 不返回裁剪信息，显示完整图片
            img_html = f'<img src="{image_url}" alt="{alt_text}" style="max-width: 100%; width: {display_width}px; height: auto; display: block; {margin_style}">'
        else:
            # 没有尺寸信息，使用默认样式
            img_html = f'<img src="{image_url}" alt="{alt_text}" style="max-width: 100%; height: auto; display: block; {margin_style}">'
        
        # 只有非grid中的图片才添加对齐div
        parent_id = block.get('parent_id', '')
        parent_block = self._find_block_by_id(blocks, parent_id) if parent_id else None
        in_grid = parent_block and parent_block.get('block_type') in [self.BLOCK_TYPE_GRID, self.BLOCK_TYPE_GRID_COLUMN]
        
        # 如果有描述，添加图片标题
        if caption:
            img_html = f'''<figure style="text-align: center;">
{img_html}
<figcaption style="font-size: 0.9em; color: #666; margin-top: 5px;">{caption}</figcaption>
</figure>'''
        
        if in_grid:
            # 在分栏布局中，图片宽度由容器控制
            img_html = f'<img src="{image_url}" alt="{alt_text}" style="width: 100%; height: auto; display: block;">'
            if caption:
                img_html = f'''<figure style="text-align: center;">
{img_html}
<figcaption style="font-size: 0.9em; color: #666; margin-top: 5px;">{caption}</figcaption>
</figure>'''
            return img_html
        elif align == 2:
            return f'<div class="layout-center">\n{img_html}\n</div>'
        elif align == 3:
            return f'<div class="layout-right">\n{img_html}\n</div>'
        else:
            return img_html
    
    def _process_image(self, token):
        """处理图片，上传到COS"""
        if token in self.image_map:
            return self.image_map[token]
        
        logger.info(f"Processing image token: {token[:30]}...")
        
        try:
            image_data = feishu_doc_api.download_image(token)
            logger.info(f"Downloaded image data: {len(image_data)} bytes")
            
            # 如果图片太大，尝试压缩
            max_size = 4 * 1024 * 1024  # 4MB
            if len(image_data) > max_size:
                logger.info(f"Image too large ({len(image_data)} bytes), compressing...")
                image_data = self._compress_image(image_data, max_size)
                logger.info(f"Compressed to {len(image_data)} bytes")
            
            if self.image_uploader:
                logger.info(f"Image uploader available: {type(self.image_uploader)}")
                from io import BytesIO
                file_obj = BytesIO(image_data)
                file_obj.name = f'{token}.png'
                file_obj.filename = f'{token}.png'
                file_obj.content_type = 'image/png'
                
                result = self.image_uploader.upload_image(file_obj)
                logger.info(f"Upload result: {result}")
                image_url = result.get('url', '')
                if not image_url:
                    logger.error("Upload returned empty URL")
                    image_url = f'feishu_image://{token}'
            else:
                logger.error("Image uploader is None")
                image_url = f'feishu_image://{token}'
            
            self.image_map[token] = image_url
            logger.info(f"Final image URL: {image_url[:50]}...")
            return image_url
            
        except Exception as e:
            logger.error(f"处理图片失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return f'feishu_image://{token}'
    
    def _compress_image(self, image_data, max_size):
        """压缩图片到指定大小以下"""
        try:
            from PIL import Image
            from io import BytesIO
            
            img = Image.open(BytesIO(image_data))
            
            # 如果图片是RGBA模式，转换为RGB
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            
            # 尝试不同的质量等级
            quality = 85
            while quality > 20:
                output = BytesIO()
                img.save(output, format='JPEG', quality=quality, optimize=True)
                compressed_data = output.getvalue()
                
                if len(compressed_data) <= max_size:
                    return compressed_data
                
                quality -= 10
            
            # 如果质量降到20还是太大，缩小尺寸
            width, height = img.size
            while len(compressed_data) > max_size and width > 800:
                width = int(width * 0.8)
                height = int(height * 0.8)
                img_resized = img.resize((width, height), Image.Resampling.LANCZOS)
                
                output = BytesIO()
                img_resized.save(output, format='JPEG', quality=70, optimize=True)
                compressed_data = output.getvalue()
            
            return compressed_data
            
        except Exception as e:
            logger.error(f"图片压缩失败: {e}")
            return image_data  # 压缩失败返回原图
    
    def _parse_divider(self, block, blocks):
        """解析分割线"""
        return '---'
    
    def _parse_callout(self, block, blocks):
        """解析高亮块"""
        callout_prop = block.get('callout', {})
        text = self._extract_text_from_property(callout_prop)
        
        return f'> {text}'
    
    def _parse_chat_card(self, block, blocks):
        """解析消息卡片"""
        return '[消息卡片]'
    
    def _parse_diagram(self, block, blocks):
        """解析流程图/UML"""
        return '[流程图/图表]'
    
    def _parse_file(self, block, blocks):
        """解析文件块"""
        file_prop = block.get('file', {})
        name = file_prop.get('name', '文件')
        token = file_prop.get('token', '')
        
        return f'[{name}](file://{token})'
    
    def _parse_block_container(self, block, blocks):
        """解析块容器（block_type=30）"""
        block_id = block.get('block_id')
        logger.info(f"Parsing block container: {block_id}")
        logger.debug(f"Block container keys: {list(block.keys())}")
        
        # 直接检查 block 中是否包含图片相关属性
        for key in block.keys():
            if 'image' in key.lower() or 'gallery' in key.lower():
                logger.debug(f"Found image-related key: {key}")
        
        children_ids = block.get('children', [])
        if children_ids:
            logger.debug(f"Block container has {len(children_ids)} children")
            return self._parse_children(block, blocks)
        
        # 检查各种可能的图片属性名
        image_keys = ['image', 'image_info', 'gallery', 'media', 'file_token', 'token']
        for key in image_keys:
            if key in block:
                logger.debug(f"Found {key} in block container")
                if key in ['image', 'image_info']:
                    return self._parse_image(block, blocks)
                elif key == 'gallery':
                    return self._parse_gallery(block, blocks)
        
        # 检查 block_type 是否为图片
        if block.get('block_type') == self.BLOCK_TYPE_IMAGE:
            return self._parse_image(block, blocks)
        
        # 尝试解析为文本
        for key in ['text', 'heading1', 'heading2', 'heading3']:
            if key in block:
                logger.debug(f"Found {key} in block container")
                return self._parse_text(block, blocks)
        
        logger.warning(f"Block container {block_id} has no recognizable content")
        return ''
    
    def _parse_gallery(self, block, blocks):
        """解析图片画廊"""
        gallery_prop = block.get('gallery', {})
        image_infos = gallery_prop.get('image_info_list', [])
        
        if not image_infos:
            children_ids = block.get('children', [])
            if children_ids:
                return self._parse_children(block, blocks)
            return ''
        
        images = []
        for img_info in image_infos:
            file_token = img_info.get('file_token', '')
            if file_token:
                image_url = self._process_image(file_token)
                images.append(f'![图片]({image_url})')
        
        if len(images) >= 2:
            return self._create_multi_column_layout(images)
        elif images:
            return images[0]
        
        return ''
    
    def _parse_children(self, block, blocks):
        """解析子块"""
        children_ids = block.get('children', [])
        
        if not children_ids:
            return ''
        
        parts = []
        for child_id in children_ids:
            child_block = self._find_block_by_id(blocks, child_id)
            if child_block:
                parsed = self._parse_block(child_block, blocks)
                if parsed:
                    parts.append(parsed)
        
        return '\n\n'.join(parts)
    
    def _parse_table_cell(self, block, blocks):
        """解析表格单元格"""
        children_ids = block.get('children', [])
        
        if not children_ids:
            return ''
        
        parts = []
        for child_id in children_ids:
            child_block = self._find_block_by_id(blocks, child_id)
            if child_block:
                parsed = self._parse_block(child_block, blocks)
                if parsed:
                    parts.append(parsed)
        
        return ' '.join(parts)
    
    def _parse_sheet(self, block, blocks):
        """解析电子表格"""
        sheet_prop = block.get('sheet', {})
        token = sheet_prop.get('token', '')
        
        logger.info(f"Parsing sheet: {token[:30] if token else 'empty'}...")
        
        if not token:
            return '[电子表格]'
        
        try:
            # token 格式：SpreadsheetToken_SheetID
            # 需要提取 SpreadsheetToken
            if '_' in token:
                spreadsheet_token = token.split('_')[0]
                logger.debug(f"Extracted spreadsheet_token: {spreadsheet_token}")
            else:
                spreadsheet_token = token
            
            # 获取电子表格内容
            sheets_data = feishu_doc_api.get_sheet_content(spreadsheet_token)
            
            logger.debug(f"Sheets data: {sheets_data}")
            
            if not sheets_data:
                logger.warning("No sheets data returned")
                return '[电子表格]'
            
            # 转换为HTML表格
            html_parts = []
            actual_sheet_index = 0  # 实际表格索引（跳过空表格后）
            for sheet_index, sheet in enumerate(sheets_data):
                sheet_title = sheet.get('title', '')
                sheet_values = sheet.get('data', [])
                column_width = sheet.get('column_width', [])
                merges = sheet.get('merges', [])
                
                # 跳过空表格
                if not sheet_values or len(sheet_values) == 0:
                    logger.debug(f"Skipping empty sheet: {sheet_title}")
                    continue
                
                # 检查是否有用户配置的列宽
                if actual_sheet_index in self.sheets_config:
                    config = self.sheets_config[actual_sheet_index]
                    column_width = config.get('column_widths', [])
                    logger.debug(f"Using custom column_width for sheet {actual_sheet_index}: {column_width}")
                elif not column_width and sheet_values:
                    # 没有用户配置且 API 没有返回列宽，使用默认值
                    column_count = len(sheet_values[0]) if sheet_values else 0
                    column_width = [100] * column_count
                    logger.debug(f"Using default column_width for sheet {sheet_index}: {column_width}")
                
                logger.debug(f"Sheet: {sheet_title}, rows: {len(sheet_values) if sheet_values else 0}, merges: {len(merges)}, column_width: {column_width}")
                
                # 不显示工作表标题
                # if len(sheets_data) > 1 and sheet_title:
                #     html_parts.append(f'<h4>{sheet_title}</h4>')
                
                if sheet_values:
                    # 构建合并单元格映射
                    merge_map = self._build_merge_map(merges)
                    
                    # 计算表格总宽度
                    total_width = sum(column_width) if column_width else 800
                    
                    # 表格样式（统一控制）
                    table_style = f'''
<style>
.sheet-table-{actual_sheet_index} {{
    border-collapse: collapse;
    width: {total_width}px;
    min-width: 100%;
    font-size: 14px;
    table-layout: fixed;
}}
.sheet-table-{actual_sheet_index} th {{
    padding: 12px 16px;
    background-color: #f5f5f5;
    font-weight: 600;
    text-align: left;
    color: #333;
    word-wrap: break-word;
    white-space: normal;
}}
.sheet-table-{actual_sheet_index} td {{
    padding: 10px 16px;
    text-align: left;
    color: #555;
    word-wrap: break-word;
    white-space: normal;
}}
.sheet-table-{actual_sheet_index} tbody tr:nth-child(odd) {{
    background-color: #ffffff;
}}
.sheet-table-{actual_sheet_index} tbody tr:nth-child(even) {{
    background-color: #fafafa;
}}
</style>
'''
                    
                    html_table = [f'<div style="overflow-x: auto; margin-bottom: 20px;">']
                    html_table.append(table_style)
                    html_table.append(f'<table class="sheet-table-{actual_sheet_index}">')
                    
                    # 构建列宽样式
                    colgroup = ['<colgroup>']
                    for i, width in enumerate(column_width):
                        if width:
                            colgroup.append(f'<col style="width: {width}px;">')
                        else:
                            colgroup.append(f'<col style="width: 100px;">')
                    colgroup.append('</colgroup>')
                    html_table.append('\n'.join(colgroup))
                    
                    for i, row in enumerate(sheet_values):
                        # 使用 thead 包裹表头行，tbody 包裹数据行
                        if i == 0:
                            html_table.append('<thead><tr>')
                        elif i == 1:
                            html_table.append('<tbody><tr>')
                        else:
                            html_table.append('<tr>')
                        
                        for j, cell in enumerate(row):
                            # 检查是否是合并单元格的一部分
                            merge_key = f"{i}_{j}"
                            if merge_key in merge_map:
                                merge_info = merge_map[merge_key]
                                # 如果是被合并的单元格（不是起始位置），跳过
                                if merge_info.get('skip'):
                                    continue
                                # 如果是合并单元格的起始位置，添加 colspan/rowspan
                                colspan = merge_info.get('colspan', 1)
                                rowspan = merge_info.get('rowspan', 1)
                                attrs = ''
                                if colspan > 1:
                                    attrs += f' colspan="{colspan}"'
                                if rowspan > 1:
                                    attrs += f' rowspan="{rowspan}"'
                            else:
                                attrs = ''
                            
                            cell_text = self._extract_cell_text(cell)
                            
                            if i == 0:
                                html_table.append(f'<th{attrs}>{cell_text}</th>')
                            else:
                                html_table.append(f'<td{attrs}>{cell_text}</td>')
                        
                        if i == 0:
                            html_table.append('</tr></thead>')
                        elif i == len(sheet_values) - 1:
                            html_table.append('</tr></tbody>')
                        else:
                            html_table.append('</tr>')
                    
                    html_table.append('</table>')
                    html_table.append('</div>')
                    html_parts.append('\n'.join(html_table))
                
                actual_sheet_index += 1  # 递增实际表格索引
            
            result = '\n'.join(html_parts) if html_parts else '[电子表格]'
            logger.debug(f"Sheet HTML result length: {len(result)}")
            return result
            
        except Exception as e:
            logger.error(f"解析电子表格失败: {e}")
            return f'[电子表格: {token[:10]}...]'
    
    def _extract_cell_text(self, cell):
        """提取单元格文本"""
        if cell is None:
            return ''
        
        # 如果是字符串，直接返回
        if isinstance(cell, str):
            return cell
        
        # 如果是数字，转换为字符串
        if isinstance(cell, (int, float)):
            return str(cell)
        
        # 如果是列表（富文本格式）
        if isinstance(cell, list):
            texts = []
            for item in cell:
                if isinstance(item, dict) and 'text' in item:
                    texts.append(item.get('text', ''))
                elif isinstance(item, str):
                    texts.append(item)
            return ''.join(texts)
        
        # 如果是字典（单个富文本段）
        if isinstance(cell, dict) and 'text' in cell:
            return cell.get('text', '')
        
        return str(cell)
    
    def _build_merge_map(self, merges):
        """构建合并单元格映射"""
        merge_map = {}
        
        if not merges:
            return merge_map
        
        for merge in merges:
            start_row = merge.get('start_row_index', 0)
            end_row = merge.get('end_row_index', 0)
            start_col = merge.get('start_column_index', 0)
            end_col = merge.get('end_column_index', 0)
            
            # 计算合并范围
            rowspan = end_row - start_row + 1
            colspan = end_col - start_col + 1
            
            # 标记起始位置
            merge_map[f"{start_row}_{start_col}"] = {
                'rowspan': rowspan,
                'colspan': colspan,
                'skip': False
            }
            
            # 标记被合并的单元格（需要跳过）
            for r in range(start_row, end_row + 1):
                for c in range(start_col, end_col + 1):
                    if r == start_row and c == start_col:
                        continue  # 跳过起始位置
                    merge_map[f"{r}_{c}"] = {'skip': True}
        
        return merge_map
    
    def _parse_grid(self, block, blocks):
        """解析分栏布局（多图同行、图文块同行）"""
        grid_prop = block.get('grid', {})
        children_ids = block.get('children', [])
        block_id = block.get('block_id')
        
        logger.info(f"Parsing grid {block_id}: {len(children_ids)} columns")
        
        if len(children_ids) == 0:
            logger.warning(f"Grid {block_id} has no children")
            return ''
        
        columns = []
        column_widths = []
        for i, child_id in enumerate(children_ids):
            child_block = self._find_block_by_id(blocks, child_id)
            if child_block:
                logger.debug(f"Grid column {i}: type={child_block.get('block_type')}, id={child_id[:20]}...")
                column_content = self._parse_grid_column(child_block, blocks)
                
                # 获取列宽比例
                column_prop = child_block.get('grid_column', {})
                width_ratio = column_prop.get('width_ratio', 50)
                column_widths.append(width_ratio)
                
                logger.debug(f"Grid column {i} content: {column_content[:100] if column_content else 'empty'}..., width_ratio: {width_ratio}")
                columns.append(column_content)
            else:
                logger.warning(f"Grid column {i} not found: {child_id}")
        
        logger.info(f"Grid parsed {len(columns)} columns, widths: {column_widths}")
        
        if len(columns) == 2:
            return self._create_two_column_layout(columns, column_widths)
        elif len(columns) == 3:
            return self._create_three_column_layout(columns, column_widths)
        elif len(columns) > 0:
            return self._create_multi_column_layout(columns, column_widths)
        else:
            return ''
    
    def _parse_grid_column(self, block, blocks):
        """解析分栏列"""
        column_prop = block.get('grid_column', {})
        width_ratio = column_prop.get('width_ratio', 50)  # 默认 50%
        
        logger.debug(f"Grid column width_ratio: {width_ratio}")
        
        children_ids = block.get('children', [])
        
        column_parts = []
        for child_id in children_ids:
            child_block = self._find_block_by_id(blocks, child_id)
            if child_block:
                parsed = self._parse_block(child_block, blocks)
                if parsed:
                    column_parts.append(parsed)
        
        return '\n\n'.join(column_parts)
    
    def _create_two_column_layout(self, columns, width_ratios=None):
        """创建双栏布局"""
        if len(columns) < 2:
            return columns[0] if columns else ''
        
        # 使用实际的 width_ratio，如果没有则平均分配
        if width_ratios and len(width_ratios) >= 2:
            ratio1 = width_ratios[0]
            ratio2 = width_ratios[1]
            # 计算百分比，考虑 gap (约 2%)
            total_ratio = ratio1 + ratio2
            width1 = round((ratio1 / total_ratio) * 98, 1)  # 留 2% 给 gap
            width2 = round((ratio2 / total_ratio) * 98, 1)
        else:
            width1 = width2 = 49.0
        
        return f'''<div style="display: flex; flex-wrap: wrap; gap: 1%; justify-content: center;">
<div style="flex: 0 0 {width1}%; text-align: center;">{columns[0]}</div>
<div style="flex: 0 0 {width2}%; text-align: center;">{columns[1]}</div>
</div>'''
    
    def _create_three_column_layout(self, columns, width_ratios=None):
        """创建三栏布局"""
        if len(columns) < 3:
            return self._create_two_column_layout(columns, width_ratios)
        
        # 使用实际的 width_ratio
        if width_ratios and len(width_ratios) >= 3:
            total_ratio = sum(width_ratios[:3])
            widths = [int((ratio / total_ratio) * 100) for ratio in width_ratios[:3]]
            widths = [min(w, 32) for w in widths]  # 减去 gap 空间
        else:
            widths = [32, 32, 32]
        
        return f'''<div style="display: flex; flex-wrap: wrap; gap: 10px; justify-content: center;">
<div style="flex: 0 0 {widths[0]}%; text-align: center;">{columns[0]}</div>
<div style="flex: 0 0 {widths[1]}%; text-align: center;">{columns[1]}</div>
<div style="flex: 0 0 {widths[2]}%; text-align: center;">{columns[2]}</div>
</div>'''
    
    def _create_multi_column_layout(self, columns, width_ratios=None):
        """创建多栏布局"""
        if not columns:
            return ''
        
        # 使用实际的 width_ratio
        if width_ratios and len(width_ratios) == len(columns):
            total_ratio = sum(width_ratios)
            widths = [int((ratio / total_ratio) * 100) for ratio in width_ratios]
            max_width = min(int(100 // len(columns)) - 2, 30)
            widths = [min(w, max_width) for w in widths]
        else:
            col_width = max(int(100 // len(columns)) - 2, 20)
            widths = [col_width] * len(columns)
        
        col_items = '\n'.join([f'<div style="flex: 0 0 {widths[i]}%; text-align: center;">{col}</div>' for i, col in enumerate(columns)])
        return f'''<div style="display: flex; flex-wrap: wrap; gap: 10px; justify-content: center;">
{col_items}
</div>'''
    
    def _extract_text(self, block):
        """从块中提取文本"""
        for key in ['text', 'heading1', 'heading2', 'heading3', 'heading4', 'heading5', 'heading6']:
            if key in block:
                return self._extract_text_from_property(block[key])
        
        return ''
    
    def _extract_text_from_property(self, prop):
        """从属性中提取文本"""
        elements = prop.get('elements', [])
        text_parts = []
        
        for elem in elements:
            text_run = elem.get('text_run', {})
            content = text_run.get('content', '')
            text_parts.append(content)
        
        return ''.join(text_parts)
    
    def parse_document_with_meta(self, doc_data, doc_token, doc_meta=None, user_token=None, sheets_config=None):
        """解析文档并返回元数据"""
        self.sheets_config = sheets_config or {}  # 存储表格配置
        markdown_content = self.parse_document(doc_data, doc_token, user_token)
        
        title = ''
        if doc_meta:
            title = doc_meta.get('title', '')
        
        if not title:
            first_heading = re.search(r'^#\s+(.+)$', markdown_content, re.MULTILINE)
            if first_heading:
                title = first_heading.group(1)
        
        return {
            'title': title or '未命名文档',
            'content': markdown_content,
            'image_count': len(self.image_map),
            'imported_at': datetime.now().isoformat()
        }


feishu_parser = FeishuDocParser()
