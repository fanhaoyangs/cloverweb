"""
COS工具类
提供图片上传和管理功能
"""

import os
import uuid
from datetime import datetime


try:
    from qcloud_cos_v5 import CosConfig, CosS3Client
    COS_AVAILABLE = True
except ImportError:
    try:
        from qcloud_cos import CosConfig, CosS3Client
        COS_AVAILABLE = True
    except ImportError:
        COS_AVAILABLE = False
        CosConfig = None
        CosS3Client = None

from config import COSConfig

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024


class COSUploader:
    """COS上传器"""
    
    def __init__(self):
        self.config = COSConfig()
        self.secret_id = self.config.SECRET_ID
        self.secret_key = self.config.SECRET_KEY
        self.region = self.config.REGION
        self.bucket_name = self.config.BUCKET_NAME
        self.custom_domain = self.config.CUSTOM_DOMAIN
        
        if not COS_AVAILABLE:
            self.client = None
            return
            
        cos_config = CosConfig(
            Region=self.region,
            SecretId=self.secret_id,
            SecretKey=self.secret_key
        )
        self.client = CosS3Client(cos_config)
    
    def upload_image(self, file_obj, filename=None):
        if not file_obj:
            raise ValueError("文件对象不能为空")
        
        original_filename = file_obj.filename or 'image.png'
        ext = os.path.splitext(original_filename)[1].lower().lstrip('.')
        
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"不支持的文件格式: .{ext}")
        
        if filename is None:
            timestamp= datetime.now().strftime('%Y%m%d%H%M%S')
            unique_id = uuid.uuid4().hex[:8]
            filename = f"{timestamp}_{unique_id}.{ext}"
        
        now = datetime.now()
        image_path = "images/{:04d}/{:02d}/{:02d}".format(
            now.year, now.month, now.day
        )
        key = f"{image_path}/{filename}"
        
        file_content = file_obj.read()
        file_obj.seek(0)
        
        if len(file_content) > MAX_FILE_SIZE:
            raise ValueError(f"文件大小不能超过 {MAX_FILE_SIZE // (1024*1024)}MB")
        
        if self.client is None:
            from config import FlaskConfig
            upload_dir = FlaskConfig.UPLOAD_FOLDER
            os.makedirs(upload_dir, exist_ok=True)
            local_path = os.path.join(upload_dir, filename)
            with open(local_path, 'wb') as f:
                f.write(file_content)
            
            from flask import url_for
            url = url_for('static', filename=f'uploads/{filename}')
            return {
                'url': url,
                'key': key,
                'size': len(file_content),
                'content_type': file_obj.content_type,
                'local': True
            }
        
        try:
            response = self.client.put_object(
                Bucket=self.bucket_name,
                Body=file_content,
                Key=key,
                ContentType=file_obj.content_type or self._get_content_type(ext)
            )
            
            url = f"https://{self.custom_domain}/{key}"
            
            return {
                'url': url,
                'key': key,
                'size': len(file_content),
                'content_type': file_obj.content_type,
                'local': False
            }
            
        except Exception as e:
            from config import FlaskConfig
            upload_dir = FlaskConfig.UPLOAD_FOLDER
            os.makedirs(upload_dir, exist_ok=True)
            local_path = os.path.join(upload_dir, filename)
            with open(local_path, 'wb') as f:
                f.write(file_content)
            
            from flask import url_for
            url = url_for('static', filename=f'uploads/{filename}')
            return {
                'url': url,
                'key': key,
                'size': len(file_content),
                'content_type': file_obj.content_type,
                'local': True,
                'fallback': True
            }
    
    def _get_content_type(self, ext):
        content_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        return content_types.get(ext, 'application/octet-stream')
    
    def list_images(self, prefix='', max_keys=1000):
        """
        获取图片列表
        
        Args:
            prefix: 前缀过滤，如 'images/2026/'
            max_keys: 最大返回数量
        
        Returns:
            list: 图片对象列表
        """
        if self.client is None:
            return []
        
        try:
            response = self.client.list_objects(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            images = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj.get('Key', '')
                    if self._is_image(key):
                        images.append({
                            'key': key,
                            'size': int(obj.get('Size', 0)),
                            'last_modified': obj.get('LastModified'),
                            'etag': obj.get('ETag', '').strip('"'),
                            'url': f"https://{self.custom_domain}/{key}",
                            'thumbnail_url': self.get_thumbnail_url(key, 200),
                            'filename': os.path.basename(key)
                        })
            
            return images
            
        except Exception as e:
            print(f"获取图片列表失败: {e}")
            return []
    
    def _is_image(self, key):
        """检查是否是图片文件"""
        ext = os.path.splitext(key)[1].lower()
        return ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']
    
    def get_thumbnail_url(self, key, size=200):
        """
        获取缩略图 URL（使用 COS 数据万象）
        
        Args:
            key: 图片 key
            size: 缩略图尺寸（宽度）
        
        Returns:
            str: 缩略图 URL
        """
        return f"https://{self.custom_domain}/{key}?imageMogr2/thumbnail/{size}x"
    
    def get_image_url(self, key):
        """获取图片完整 URL"""
        return f"https://{self.custom_domain}/{key}"
    
    def delete_image(self, key):
        """删除图片"""
        if self.client is None:
            return False
        
        try:
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return True
        except Exception as e:
            print(f"删除图片失败: {e}")
            return False
    
    @staticmethod
    def is_configured():
        if not COS_AVAILABLE:
            return False
        config = COSConfig()
        return bool(config.SECRET_ID and config.SECRET_KEY)


_uploader = None


def get_uploader():
    global _uploader
    if _uploader is None:
        _uploader = COSUploader()
    return _uploader
