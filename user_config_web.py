# user_config_web.py - 使用 Supabase 存储图片
import os

class UserConfig:
    """用户配置类 - 云端版"""

    def __init__(self):
        # Supabase 存储的基础 URL
        self.supabase_url = "https://trkqbyuwwchmoijcmeas.supabase.co/storage/v1/object/public/images"
        
        # 噩梦高考图片（考试通过/失败）
        self.pass_photo_path = f"{self.supabase_url}/nightmare_exam/pass.png"
        self.fail_photo_path = f"{self.supabase_url}/nightmare_exam/fail.png"
        self.evelyn_photo_path = f"{self.supabase_url}/nightmare_exam/evelyn.png"
        
        # 版型图片文件夹
        self.base_path = f"{self.supabase_url}/templates_images"
        
        # 万圣之夜图片文件夹
        self.image_path = f"{self.supabase_url}/halloween"

    def get_current_user(self):
        """获取当前登录用户信息"""
        from flask import session
        from app import get_user_settings
        user = session.get('user')
        if user:
            settings = get_user_settings(user['id'])
            return settings.get('user_name', '用户'), settings.get('student_id', '')
        return '未登录', ''

    def get_photo_paths(self):
        """获取通过/失败图片路径"""
        return self.pass_photo_path, self.fail_photo_path

    def get_evelyn_photo_path(self):
        """获取伊芙琳图片路径"""
        return self.evelyn_photo_path

    def get_base_path(self):
        """获取版型图片文件夹路径"""
        return self.base_path

    def get_image_path(self):
        """获取万圣之夜图片文件夹路径"""
        return self.image_path

    def get_background_path(self):
        """背景图片路径（暂未使用）"""
        return ""

    def get_background_video(self):
        """背景视频路径（暂未使用）"""
        return ""


# 创建全局配置实例
user_config = UserConfig()