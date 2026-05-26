# user_config_web.py - 网页版用户配置（替代 user_manager.py）
import os
from settings_web import get_all_settings

class UserConfig:
    """用户配置类 - 网页版"""

    def __init__(self):
        settings = get_all_settings()
        self.current_user = settings.get('user_name', '崔朕')
        self.current_student_id = settings.get('student_id', '20231719')
        # 修改为你实际的图片路径
        self.pass_photo_path = r"C:\Users\HP\PycharmProjects\PythonProject8\.venv\噩梦高考图片\通过.png"
        self.fail_photo_path = r"C:\Users\HP\PycharmProjects\PythonProject8\.venv\噩梦高考图片\挂科.png"
        self.evelyn_photo_path = r"C:\Users\HP\PycharmProjects\PythonProject8\.venv\噩梦高考图片\伊芙琳的堕落之血.png"
        self.base_path = r"C:\Users\HP\PycharmProjects\PythonProject8\.venv\版型图片"
        self.image_path = r"C:\Users\HP\PycharmProjects\PythonProject8\.venv\万圣之夜"
        self.background_path = r"C:\Users\HP\PycharmProjects\PythonProject8\.venv\背景内容"
        self.background_video = r"C:\Users\HP\PycharmProjects\PythonProject8\.venv\背景内容\开始界面背景视频.mp4"

    def get_background_path(self):
        return self.background_path

    def get_background_video(self):
        return self.background_video

    def get_current_user(self):
        return self.current_user, self.current_student_id

    def get_photo_paths(self):
        return self.pass_photo_path, self.fail_photo_path

    def get_evelyn_photo_path(self):
        return self.evelyn_photo_path

    def get_base_path(self):
        return self.base_path

    def get_image_path(self):
        return self.image_path


# 创建全局配置实例
user_config = UserConfig()