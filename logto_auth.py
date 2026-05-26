"""
Logto 认证配置模块
用于集成 Logto 云服务的登录功能
"""

import os
from logto import LogtoClient, LogtoConfig
from logto.constants import UserScope
from flask import session, redirect, url_for, request
from functools import wraps

# ========== 配置区域 ==========
# 从环境变量读取 Logto 配置
LOGTO_ENDPOINT = os.getenv('LOGTO_ENDPOINT')
LOGTO_APP_ID = os.getenv('LOGTO_APP_ID')
LOGTO_APP_SECRET = os.getenv('LOGTO_APP_SECRET')
LOGTO_REDIRECT_URI = os.getenv('LOGTO_REDIRECT_URI', 'http://localhost:5000/callback')

# 初始化 Logto 客户端
client = LogtoClient(
    LogtoConfig(
        endpoint=LOGTO_ENDPOINT,
        appId=LOGTO_APP_ID,
        appSecret=LOGTO_APP_SECRET,
        resources=[],  # API 资源，暂时为空
        scopes=[  # 请求的用户信息范围
            UserScope.OPENID,
            UserScope.PROFILE,
            UserScope.EMAIL,
        ],
    ),
)

def login_required(f):
    """
    登录验证装饰器
    用法：在需要登录才能访问的路由函数上面加上 @login_required
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 检查 session 中是否有用户信息
        if 'user' not in session:
            # 未登录，保存当前页面地址，登录后跳转回来
            session['next_url'] = request.url
            # 重定向到登录页
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """获取当前登录用户信息"""
    return session.get('user', None)