"""
一次性管理命令：为 5 个 article-block section 各创建 1 条 published Article
用于演示/验证前端 inject 效果。生产环境可删除此文件。
"""
from django.core.management.base import BaseCommand
from apps.content.models import Article, Category
from django.utils import timezone


# 5 条种子数据：每条对应一个 website_section
SEED_ARTICLES = [
    {
        'title': '社区花园：从城市角落到共治空间',
        'slug': 'community-garden-co-governance',
        'excerpt': '从一片闲置绿地到居民共建的社区客厅，社区花园正在重新定义城市公共生活的可能。',
        'cover_image': 'https://images.communitygarden.org.cn/communitygarden/四叶草堂LOGO.png',
        'section': 'home_news',
    },
    {
        'title': '同济大学·四叶草堂：让自然回到日常生活',
        'slug': 'tongji-clover-let-nature-return',
        'excerpt': '四叶草堂团队十余年深耕社区花园与社区营造，把自然带回到每一个普通人的日常。',
        'cover_image': 'https://images.communitygarden.org.cn/communitygarden/四叶草堂LOGO.png',
        'section': 'clover_media',
    },
    {
        'title': '社区营造主题沙龙 · 第 18 期：与孩子共建一座花园',
        'slug': 'salon-18-kids-garden',
        'excerpt': '本期沙龙邀请家长、设计师、教育者共同探讨：什么样的花园才是孩子真正需要的？',
        'cover_image': 'https://images.communitygarden.org.cn/communitygarden/四叶草堂LOGO.png',
        'section': 'philosophy_salon',
    },
    {
        'title': '《城市微更新：社区花园的中国实践》',
        'slug': 'publication-urban-micro-renewal',
        'excerpt': '本书汇集了过去十年中国社区花园的典型案例，呈现从设计到运营的完整路径。',
        'cover_image': 'https://images.communitygarden.org.cn/communitygarden/四叶草堂LOGO.png',
        'section': 'philosophy_publications',
    },
    {
        'title': '案例 · 上海创智农园：六年的共生实验',
        'slug': 'case-chuangzhi-farm-6-years',
        'excerpt': '从 2018 年开放至今，创智农园已接待访客 12 万人次，成为上海最具代表性的社区花园之一。',
        'cover_image': 'https://images.communitygarden.org.cn/communitygarden/四叶草堂LOGO.png',
        'section': 'philosophy_cases',
    },
]


class Command(BaseCommand):
    help = '为 5 个 article-block section 各创建 1 条 published Article（演示/验证用）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clean',
            action='store_true',
            help='先删除同 slug 的 Article 再创建（用于重跑）',
        )

    def handle(self, *args, **options):
        created, updated, skipped = 0, 0, 0
        for data in SEED_ARTICLES:
            section = data.pop('section')
            if options['clean']:
                Article.objects.filter(slug=data['slug']).delete()
            obj, is_created = Article.objects.update_or_create(
                slug=data['slug'],
                defaults={
                    **data,
                    'content_html': f"<p>{data['excerpt']}</p><p>占位内容，后续由 CMS 后台编辑。</p>",
                    'status': 'published',
                    'published_at': timezone.now(),
                    'website_sections': [section],
                    'section_order': 0,
                },
            )
            if is_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f'  ✓ 创建 {obj.slug} → {section}'))
            else:
                updated += 1
                self.stdout.write(f'  ↻ 更新 {obj.slug} → {section}')

        self.stdout.write(self.style.SUCCESS(
            f'\n完成：{created} 新建 / {updated} 更新 / {skipped} 跳过'
        ))
