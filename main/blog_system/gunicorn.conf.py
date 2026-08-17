"""
Gunicorn配置文件
用于生产环境部署
"""
import os

# 服务器配置
bind = os.environ.get('GUNICORN_BIND', '127.0.0.1:5000')
backlog = 2048

# 工作进程配置
workers = 2
worker_class = 'sync'
worker_connections = 1000
timeout = 120
keepalive = 5

# 进程名称
proc_name = 'blog_system'

# 日志配置
errorlog = '-'
accesslog = '-'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 进程管理
pidfile = 'blog_system.pid'
umask = 0
user = None
group = None
tmp_upload_dir = '/tmp/blog_system_uploads'

# 预加载应用（减少内存占用）
preload_app = True

def on_starting(server):
    """服务启动前调用"""
    pass

def on_reload(server):
    """重新加载时调用"""
    pass

def worker_int(worker):
    """工作进程中断时调用"""
    pass

def worker_abort(worker):
    """工作进程终止时调用"""
    pass
