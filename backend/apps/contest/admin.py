from django.contrib import admin

from .models import Ranking, Score, Season, Submission, Team


class TeamInline(admin.TabularInline):
    model = Team
    extra = 0


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'status', 'start_at', 'end_at')
    list_filter = ('status',)
    inlines = [TeamInline]


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'season', 'leader', 'created_at')
    list_filter = ('season',)
    search_fields = ('name',)
    filter_horizontal = ('members',)


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('title', 'team', 'season', 'status', 'submitted_at', 'reviewed_at')
    list_filter = ('status', 'season')
    search_fields = ('title', 'team__name')


@admin.register(Score)
class ScoreAdmin(admin.ModelAdmin):
    list_display = ('submission', 'judge', 'score', 'created_at')
    list_filter = ('judge',)


@admin.register(Ranking)
class RankingAdmin(admin.ModelAdmin):
    list_display = ('season', 'rank', 'team', 'total_score', 'published_at')
    list_filter = ('season',)
