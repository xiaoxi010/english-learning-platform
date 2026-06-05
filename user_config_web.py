# user_config_web.py - 用于Render部署的清理版
class UserConfig:
    """用户配置类 - Render部署用"""

    def __init__(self):
        # 所有图片路径都置为空，让功能暂时不崩溃
        self.pass_photo_path = ""
        self.fail_photo_path = ""
        self.evelyn_photo_path = ""
        self.base_path = ""
        self.image_path = ""

    def get_current_user(self):
        # 直接从session获取用户信息
        from flask import session
        user = session.get('user')
        if user:
            return user.get('name', '用户'), ''
        return '未登录', ''

    # 其他所有get_xxx方法都返回空字符串
    def get_photo_paths(self):
        return self.pass_photo_path, self.fail_photo_path

    def get_evelyn_photo_path(self):
        return self.evelyn_photo_path

    def get_base_path(self):
        return self.base_path

    def get_image_path(self):
        return self.image_path

    def get_background_path(self):
        return ""

    def get_background_video(self):
        return ""

user_config = UserConfig()