"""从 main/ 旧静态页提取内容，写入 SitePage 表。

用法：
    python manage.py seed_sitepages --src ../main

处理逻辑：
1. 提取 <head> 里的全局 <style>（第一个 style 块）
2. 提取 </nav> 到 <footer> 之间的正文区（丢弃旧导航/页脚/脚本，Vue 布局已有）
3. 提取正文区里的内联 <style> 一并收编
4. 全部 CSS 做 scope 变换（选择器加 .sitepage-<slug> 前缀，避免污染 Vue 全局样式）
5. 组装 content_html 存入 SitePage
"""
import re
from pathlib import Path

import tinycss2
from tinycss2.ast import AtRule, QualifiedRule
from django.core.management.base import BaseCommand, CommandError

from apps.team.models import SitePage

PAGES = [
    ('home', '花开中国｜首页', 'index.html'),
    ('philosophy', '理念路径 - 花开中国', 'philosophy.html'),
    ('clover', '四叶草堂 - 重塑家园 共生发展', 'clover.html'),
    # about 暂留空：main/ 没有 about.html，CMS 后台 (/admin/sitepages) 可手填
    # ('about', '关于我们', None),
]

FONT_IMPORT = (
    "@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC"
    ":wght@300;400;500;700&family=Noto+Serif+SC:wght@400;700&display=swap');"
)

ROOT_SELECTORS = {'html', 'body', ':root'}
SKIP_AT_KEYWORDS = {'font-face', 'keyframes', '-webkit-keyframes', 'charset', 'import'}


def split_top_level(s):
    """顶层逗号切分（忽略括号内的逗号，如 :not(.a, .b)）。"""
    parts, depth, cur = [], 0, ''
    for ch in s:
        if ch in '([':
            depth += 1
        elif ch in ')]':
            depth -= 1
        if ch == ',' and depth == 0:
            parts.append(cur)
            cur = ''
        else:
            cur += ch
    if cur.strip():
        parts.append(cur)
    return parts


def scope_selector(sel, scope):
    sel = sel.strip()
    if not sel:
        return None
    out = []
    for p in split_top_level(sel):
        pl = p.strip().lower()
        if not pl:
            continue
        if pl == '*':
            out.append(f'{scope} *')
        elif pl in ROOT_SELECTORS:
            out.append(scope)
        elif pl.startswith(':root'):
            out.append(scope + p.strip()[5:])
        else:
            out.append(f'{scope} {p.strip()}')
    return ', '.join(out)


def scope_rules(nodes, scope):
    """递归 scope 一组规则节点。"""
    out = []
    for n in nodes:
        if isinstance(n, QualifiedRule):
            sel = tinycss2.serialize(n.prelude).strip()
            new_sel = scope_selector(sel, scope)
            if new_sel:
                n.prelude = tinycss2.parse_component_value_list(new_sel)
                out.append(n)
        elif isinstance(n, AtRule):
            kw = n.lower_at_keyword
            if kw in ('media', 'supports') and n.content is not None:
                inner = tinycss2.parse_rule_list(n.content)
                scoped_inner = scope_rules(inner, scope)
                out.append(AtRule(
                    n.source_line, n.source_column,
                    n.at_keyword, n.lower_at_keyword,
                    n.prelude,
                    tinycss2.parse_component_value_list(
                        tinycss2.serialize(scoped_inner)
                    ),
                ))
            elif kw not in SKIP_AT_KEYWORDS:
                out.append(n)
            else:
                out.append(n)  # @font-face / @keyframes 原样保留
        else:
            out.append(n)
    return out


def scope_css(css, scope):
    rules = tinycss2.parse_stylesheet(css, skip_comments=True, skip_whitespace=True)
    scoped = scope_rules(rules, scope)
    return tinycss2.serialize(scoped)


def extract(html):
    """返回 (全局css, 正文html, 内联css列表)。"""
    styles = re.findall(r'<style[^>]*>(.*?)</style>', html, re.S)
    global_css = styles[0] if styles else ''

    m = re.search(r'</nav>(.*?)<footer', html, re.S)
    if not m:
        raise ValueError('未找到 </nav>...<footer> 内容区')
    content = m.group(1)

    inline_styles = re.findall(r'<style[^>]*>(.*?)</style>', content, re.S)
    content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.S)
    content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.S)
    return global_css, content.strip(), inline_styles


class Command(BaseCommand):
    help = '从 main/ 旧静态页提取内容写入 SitePage'

    def add_arguments(self, parser):
        parser.add_argument('--src', required=True, help='main 目录路径')

    def handle(self, *args, **opts):
        src = Path(opts['src']).resolve()
        if not src.is_dir():
            raise CommandError(f'目录不存在: {src}')

        for slug, title, filename in PAGES:
            path = src / filename
            if not path.exists():
                self.stderr.write(self.style.WARNING(f'跳过 {filename}（不存在）'))
                continue
            html = path.read_text(encoding='utf-8')
            global_css, content, inline_styles = extract(html)

            scope = f'.sitepage-{slug}'
            all_css = global_css + '\n' + '\n'.join(inline_styles)
            scoped = FONT_IMPORT + '\n' + scope_css(all_css, scope)

            content_html = (
                f'<div class="sitepage {scope}">\n{content}\n</div>\n'
                f'<style>\n{scoped}\n</style>'
            )

            obj, created = SitePage.objects.update_or_create(
                slug=slug,
                defaults={'title': title, 'content_html': content_html},
            )
            action = '创建' if created else '更新'
            self.stdout.write(self.style.SUCCESS(
                f'{action} sitepage:{slug} ← {filename} '
                f'(内容 {len(content)} 字符, CSS {len(scoped)} 字符)'
            ))
