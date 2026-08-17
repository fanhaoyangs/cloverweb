from django.urls import path

from . import views_ueditor

app_name = 'common'

urlpatterns = [
    # UEditorPlus 统一入口：/api/ueditor/?action=config|uploadimage|catchimage|listimage...
    path('', views_ueditor.ueditor_entry, name='ueditor'),
]
