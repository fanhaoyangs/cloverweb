from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = 'CloverWeb 后台管理'
admin.site.site_title = 'CloverWeb'
admin.site.index_title = '内容管理'

urlpatterns = [
    # Django admin 挂 /django-admin/（D5 修正：避免与前端 /admin 路由冲突）
    path('django-admin/', admin.site.urls),
    # API
    path('api/auth/', include('apps.auth_custom.urls')),
    path('api/ueditor/', include('apps.common.urls')),
    path('api/', include('apps.content.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
