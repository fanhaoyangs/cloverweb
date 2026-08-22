"""幂等创建论坛板块（与设计方案 P1 板块清单一致）。"""
from django.core.management.base import BaseCommand

from apps.bbs.models import Node

# (slug, name, description, icon, order, staff_only)
NODES = [
    ('garden', '花园行动', '社区花园营造案例、动手日志、志愿者招募', '🌱', 0, False),
    ('contest', '竞赛参与', '竞赛报名、组队互助、作品交流', '🏆', 1, False),
    ('activity', '共建活动', '工作坊、沙龙、开放日的报名与回顾', '🌻', 2, False),
    ('general', '经验互助', '种植技巧、材料分享、求助答疑', '💬', 3, False),
    ('notice', '站务公告', '官方公告与规则发布（仅管理员发帖）', '📢', 4, True),
]


class Command(BaseCommand):
    help = '按板块清单创建/补齐论坛板块（幂等，按 slug update_or_create）'

    def handle(self, *args, **options):
        created = 0
        for slug, name, desc, icon, order, staff_only in NODES:
            _, is_created = Node.objects.update_or_create(
                slug=slug,
                defaults={
                    'name': name, 'description': desc, 'icon': icon,
                    'order': order, 'staff_only': staff_only, 'is_active': True,
                },
            )
            if is_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f'  ✓ 创建 {slug} / {name}'))
            else:
                self.stdout.write(f'  ↻ 已存在 {slug} / {name}')
        self.stdout.write(self.style.SUCCESS(f'完成：新增 {created} 个板块'))
