from django.conf import settings
from django.db import models


class Season(models.Model):
    """社区花园竞赛：届/赛季。"""

    STATUS_CHOICES = [
        ('upcoming', '未开始'),
        ('ongoing', '进行中'),
        ('finished', '已结束'),
    ]

    name = models.CharField('名称', max_length=128)
    slug = models.SlugField('标识', max_length=128, unique=True)
    status = models.CharField('状态', max_length=16, choices=STATUS_CHOICES, default='upcoming')
    start_at = models.DateTimeField('开始时间', null=True, blank=True)
    end_at = models.DateTimeField('结束时间', null=True, blank=True)
    rules_html = models.TextField('规则/说明 HTML', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '竞赛赛季'
        verbose_name_plural = '竞赛赛季'
        ordering = ['-start_at']

    def __str__(self):
        return self.name


class Team(models.Model):
    season = models.ForeignKey(
        Season, on_delete=models.CASCADE, related_name='teams', verbose_name='赛季',
    )
    name = models.CharField('队伍名', max_length=128)
    leader = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='led_teams', verbose_name='队长',
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name='teams', verbose_name='成员',
    )
    contact = models.CharField('联系方式', max_length=128, blank=True)
    created_at = models.DateTimeField('报名时间', auto_now_add=True)

    class Meta:
        verbose_name = '参赛队伍'
        verbose_name_plural = '参赛队伍'
        constraints = [
            models.UniqueConstraint(fields=['season', 'name'], name='uniq_team_in_season'),
        ]

    def __str__(self):
        return f'{self.season} - {self.name}'


class Submission(models.Model):
    STATUS_CHOICES = [
        ('pending', '待审核'),
        ('approved', '已通过'),
        ('rejected', '已退回'),
    ]

    season = models.ForeignKey(
        Season, on_delete=models.CASCADE, related_name='submissions', verbose_name='赛季',
    )
    team = models.ForeignKey(
        Team, on_delete=models.CASCADE, related_name='submissions', verbose_name='队伍',
    )
    title = models.CharField('作品标题', max_length=200)
    content_html = models.TextField('作品说明 HTML', blank=True)
    images = models.JSONField('图片 URL 列表', default=list, blank=True)
    status = models.CharField('状态', max_length=16, choices=STATUS_CHOICES, default='pending')
    submitted_at = models.DateTimeField('提交时间', auto_now_add=True)
    reviewed_at = models.DateTimeField('审核时间', null=True, blank=True)

    class Meta:
        verbose_name = '参赛作品'
        verbose_name_plural = '参赛作品'
        ordering = ['-submitted_at']

    def __str__(self):
        return self.title


class Score(models.Model):
    submission = models.ForeignKey(
        Submission, on_delete=models.CASCADE, related_name='scores', verbose_name='作品',
    )
    judge = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='评委',
    )
    score = models.PositiveSmallIntegerField('分数')
    comment = models.TextField('评语', blank=True)
    created_at = models.DateTimeField('评分时间', auto_now_add=True)

    class Meta:
        verbose_name = '评分'
        verbose_name_plural = '评分'
        constraints = [
            models.UniqueConstraint(fields=['submission', 'judge'], name='uniq_score_per_judge'),
        ]

    def __str__(self):
        return f'{self.submission} - {self.judge} - {self.score}'


class Ranking(models.Model):
    season = models.ForeignKey(
        Season, on_delete=models.CASCADE, related_name='rankings', verbose_name='赛季',
    )
    team = models.ForeignKey(
        Team, on_delete=models.CASCADE, related_name='rankings', verbose_name='队伍',
    )
    rank = models.PositiveSmallIntegerField('名次')
    total_score = models.PositiveIntegerField('总分', default=0)
    remark = models.CharField('备注', max_length=255, blank=True)
    published_at = models.DateTimeField('公布时间', null=True, blank=True)

    class Meta:
        verbose_name = '排名'
        verbose_name_plural = '排名'
        ordering = ['rank']
        constraints = [
            models.UniqueConstraint(fields=['season', 'team'], name='uniq_ranking_in_season'),
        ]

    def __str__(self):
        return f'{self.season} 第{self.rank}名 {self.team}'
