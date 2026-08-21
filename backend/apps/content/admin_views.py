"""CMS 管理 API 视图（仅 is_staff，飞书登录用户 / superuser）。"""
from django.db.models import Q
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.team.models import SitePage

from .admin_serializers import (
    RESERVED_SLUGS,
    ArticleAdminListSerializer,
    ArticleAdminSerializer,
    CategoryAdminSerializer,
    SitePageAdminListSerializer,
    SitePageAdminSerializer,
)
from .models import Article, Category


class AdminPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class AdminArticleListView(generics.ListCreateAPIView):
    """GET /api/admin/articles/?status=&search=&category=&page=
    POST /api/admin/articles/（author 自动取当前用户）
    列表不含 content_html（列表页不显示正文，大幅减小响应）。
    """

    serializer_class = ArticleAdminSerializer
    permission_classes = [AdminPermission]

    def get_serializer_class(self):
        return ArticleAdminListSerializer if self.request.method == 'GET' else ArticleAdminSerializer

    def get_queryset(self):
        qs = Article.objects.select_related('category', 'author').prefetch_related('tags')
        params = self.request.query_params
        status = params.get('status')
        if status:
            qs = qs.filter(status=status)
        category = params.get('category')
        if category:
            qs = qs.filter(category__slug=category)
        search = params.get('search')
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(excerpt__icontains=search))
        return qs


class AdminArticleDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ArticleAdminSerializer
    permission_classes = [AdminPermission]
    queryset = Article.objects.select_related('category', 'author').prefetch_related('tags')


class AdminCategoryListView(generics.ListCreateAPIView):
    serializer_class = CategoryAdminSerializer
    permission_classes = [AdminPermission]
    queryset = Category.objects.all().order_by('order', 'id')

    def perform_create(self, serializer):
        # slug 缺省自动生成（SlugField 仅 ascii，中文名无法直接用）
        if not serializer.validated_data.get('slug'):
            from django.utils.text import slugify
            name = serializer.validated_data['name']
            base = slugify(name) or 'cat'
            slug = base
            i = 1
            while Category.objects.filter(slug=slug).exists():
                i += 1
                slug = f'{base}-{i}'
            serializer.save(slug=slug[:64])
        else:
            serializer.save()


class AdminSitePageListView(generics.ListCreateAPIView):
    """GET /api/admin/sitepages/?status=
    POST /api/admin/sitepages/（slug 缺省按 title 自动生成）
    列表不含 content_html（编辑时单独拉详情）。
    """

    serializer_class = SitePageAdminSerializer
    permission_classes = [AdminPermission]
    queryset = SitePage.objects.all().order_by('menu_order', 'created_at', 'id')

    def get_serializer_class(self):
        return SitePageAdminListSerializer if self.request.method == 'GET' else SitePageAdminSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        status = self.request.query_params.get('status')
        if status:
            qs = qs.filter(status=status)
        return qs

    def perform_create(self, serializer):
        from django.utils.text import slugify

        slug = serializer.validated_data.get('slug')
        if not slug:
            base = slugify(serializer.validated_data.get('title') or '') or 'page'
            slug, i = base, 1
            while SitePage.objects.filter(slug=slug).exists() or slug in RESERVED_SLUGS:
                i += 1
                slug = f'{base}-{i}'
        serializer.save(slug=slug[:64], updated_by=self.request.user)


class AdminSitePageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PUT/PATCH/DELETE /api/admin/sitepages/<slug>/
    状态：草稿(draft)/已发布(published)/已撤下(archived)；DELETE 物理删除。
    """

    serializer_class = SitePageAdminSerializer
    permission_classes = [AdminPermission]
    queryset = SitePage.objects.all()
    lookup_field = 'slug'

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class AdminImageCropView(APIView):
    """POST /api/admin/images/crop/ 服务端裁切图片并上传 COS。

    入参：{url, x, y, width, height}（自然像素坐标）。服务端下载 → Pillow 裁切 →
    上传 COS → 返回 {url}。彻底规避前端 canvas 的跨域(CORS)与同源图缓存问题。
    """

    permission_classes = [AdminPermission]

    def post(self, request):
        import io

        import requests as http

        from PIL import Image as PILImage

        from apps.common import cos

        url = (request.data.get('url') or '').strip()
        try:
            x = int(request.data.get('x'))
            y = int(request.data.get('y'))
            width = int(request.data.get('width'))
            height = int(request.data.get('height'))
        except (TypeError, ValueError):
            return Response({'detail': '裁切参数无效'}, status=400)
        if not url or width <= 0 or height <= 0:
            return Response({'detail': '参数无效'}, status=400)

        try:
            resp = http.get(url, timeout=20, headers={'User-Agent': 'Mozilla/5.0 CloverWeb'})
            if resp.status_code != 200:
                return Response({'detail': f'下载图片失败 HTTP {resp.status_code}'}, status=502)
            img = PILImage.open(io.BytesIO(resp.content))
            img.load()
        except Exception as exc:  # noqa: BLE001
            return Response({'detail': f'图片解析失败: {exc}'}, status=400)

        iw, ih = img.size
        x = min(max(x, 0), iw)
        y = min(max(y, 0), ih)
        width = min(width, iw - x)
        height = min(height, ih - y)
        if width <= 0 or height <= 0:
            return Response({'detail': '裁切区域超出图片范围'}, status=400)

        cropped = img.crop((x, y, x + width, y + height))
        # 透明图保留 PNG，其余转 JPEG（与 views_ueditor._compress_image 策略一致），避免照片裁切后体积暴增
        buf = io.BytesIO()
        if cropped.mode in ('RGBA', 'LA') or (cropped.mode == 'P' and 'transparency' in cropped.info):
            cropped.save(buf, format='PNG')
            ext, mime = '.png', 'image/png'
        else:
            if cropped.mode != 'RGB':
                cropped = cropped.convert('RGB')
            cropped.save(buf, format='JPEG', quality=80, optimize=True)
            ext, mime = '.jpg', 'image/jpeg'
        try:
            key = cos.build_object_key('images', ext)
            new_url = cos.upload_bytes(key, buf.getvalue(), mime)
        except cos.CosNotConfigured as exc:
            return Response({'detail': str(exc)}, status=503)
        except Exception as exc:  # noqa: BLE001
            return Response({'detail': f'上传失败: {exc}'}, status=500)
        return Response({'url': new_url})
