"""幂等创建文章分类：与前台新闻页 CATEGORIES 对齐（web/src/api/article.js）。

slug 与前台 CATEGORIES 的 value 保持一致，保证文章 category 在前台新闻页能正确过滤显示。
可重复执行：按 slug update_or_create，仅补缺失、不删改已有分类。
"""
from django.core.management.base import BaseCommand

from apps.content.models import Category

# (slug, name) —— 与 web/src/api/article.js 的 CATEGORIES 对齐
CATEGORIES = [
    ('news', '新闻资讯'),
    ('project', '项目案例'),
    ('competition', '竞赛信息'),
    ('media', '媒体报道'),
    ('activity', '活动动态'),
    ('publication', '学术出版'),
    ('other', '其他'),
]


class Command(BaseCommand):
    help = '按前台新闻页分类清单创建/补齐文章分类（幂等）'

    def handle(self, *args, **options):
        created = 0
        for order, (slug, name) in enumerate(CATEGORIES):
            obj, is_created = Category.objects.update_or_create(
                slug=slug,
                defaults={'name': name, 'order': order},
            )
            if is_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f'  ✓ 创建 {slug} / {name}'))
            else:
                self.stdout.write(f'  ↻ 已存在 {slug} / {name}')
        self.stdout.write(self.style.SUCCESS(f'完成：新增 {created} 个分类'))
