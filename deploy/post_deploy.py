"""部署后数据初始化（幂等），由 deploy.sh 第 5 步调用。

- 静态页初始 fixture：仅当 SitePage 表为空时加载（首次部署）。
  不能无条件 loaddata——fixture 是老版本导出、不含 status/in_menu/
  menu_label 字段，重复加载会把线上已发布页面整体覆盖回旧状态
  （status 重置为 draft 导致主页 404、菜单配置全部丢失）。
- seed_categories：按 slug update_or_create，天然幂等，每次执行补齐缺失分类。
"""
import os
import sys

# 脚本位于 deploy/，django 项目在 ../backend —— 显式加入 sys.path
# （直接 python deploy/post_deploy.py 运行时 sys.path[0] 是 deploy/）
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backend'))

import django  # noqa: E402

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cloverweb.settings.prod')
django.setup()

from django.core.management import call_command  # noqa: E402

from apps.team.models import SitePage  # noqa: E402

if SitePage.objects.exists():
    print('  静态页已有数据，跳过 loaddata（保护线上发布状态与菜单配置）')
else:
    call_command('loaddata', 'apps/team/fixtures/initial_sitepages.json')
    print('  静态页为空，已加载初始 fixture')

call_command('seed_categories')
