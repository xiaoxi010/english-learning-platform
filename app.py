# app.py - Flask网页版主程序（集成Logto登录 + Supabase数据库）
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, session, jsonify, redirect, url_for, request
import os
from logto import LogtoClient, LogtoConfig
from asgiref.sync import async_to_sync
import psycopg2
from psycopg2.extras import RealDictCursor
#from vocabulary_web import vocabulary_bp
from recitation_web import recitation_bp
#from exam_web import exam_bp
from past_light_web import past_light_bp
from shadow_exam_web import shadow_bp
from seventy_two_web import seventy_two_bp
from thirty_six_web import thirty_six_bp
from treasure_web import treasure_bp
from halloween_web import halloween_bp  
from shadow_hunter_web import shadow_hunter_bp
from shadow_hunter_png import shadow_hunter_png_bp
#from skill_db_web import skill_db_bp
from nightmare_exam_web import nightmare_bp
#from settings_web import settings_bp, get_all_settings

app = Flask(__name__)
app.secret_key = 'english-platform-secret-key'

# ========== Supabase 数据库配置 ==========
DATABASE_URL = "postgresql://postgres:WqP9V1bZJjBiOfvv@db.trkqbyuwwchmoijcmeas.supabase.co:5432/postgres"

def get_db_connection():
    """获取数据库连接"""
    return psycopg2.connect(DATABASE_URL)

def init_db():
    """初始化数据库（仅在需要时执行一次）"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 创建 settings 表（如果不存在）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id BIGSERIAL PRIMARY KEY,
            user_id TEXT NOT NULL UNIQUE,
            user_name TEXT DEFAULT '未设置',
            student_id TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # 创建 exam_stats 表（如果不存在）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS exam_stats (
            id BIGSERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            exam_type TEXT,
            score INTEGER,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # 创建 skill_database 表（如果不存在）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS skill_database (
            id BIGSERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            skill_name TEXT,
            skill_level INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # 创建索引
    cur.execute("CREATE INDEX IF NOT EXISTS idx_settings_user_id ON settings(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_exam_stats_user_id ON exam_stats(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_skill_database_user_id ON skill_database(user_id)")
    
    conn.commit()
    cur.close()
    conn.close()
    print("数据库初始化完成")

# 启动时初始化数据库（可选，如果表已存在可以注释掉）
# init_db()
# =========================================

# ========== Logto 初始化配置 ==========
logto_config = LogtoConfig(
    endpoint=os.getenv('LOGTO_ENDPOINT'),
    appId=os.getenv('LOGTO_APP_ID'),
    appSecret=os.getenv('LOGTO_APP_SECRET'),
)
logto_client = LogtoClient(logto_config)
# =====================================

# 注册所有蓝图
app.register_blueprint(vocabulary_bp)
app.register_blueprint(recitation_bp)
app.register_blueprint(exam_bp)
app.register_blueprint(past_light_bp)
app.register_blueprint(shadow_bp)
app.register_blueprint(seventy_two_bp)
app.register_blueprint(thirty_six_bp)
app.register_blueprint(treasure_bp)
app.register_blueprint(halloween_bp)  
app.register_blueprint(shadow_hunter_bp) 
app.register_blueprint(shadow_hunter_png_bp)
app.register_blueprint(skill_db_bp, url_prefix='/skill_db')
app.register_blueprint(nightmare_bp, url_prefix='/nightmare')
app.register_blueprint(settings_bp)

# ========== Logto 登录路由 ==========
@app.route('/login')
def login():
    """跳转到 Logto 登录页面"""
    session['next_url'] = request.args.get('next', url_for('index'))
    sign_in_uri = async_to_sync(logto_client.signIn)(
        os.getenv('LOGTO_REDIRECT_URI')
    )
    return redirect(sign_in_uri)

@app.route('/callback')
def callback():
    """Logto 登录成功后的回调"""
    try:
        callback_uri = request.url
        async_to_sync(logto_client.handleSignInCallback)(callback_uri)
        user_info_obj = async_to_sync(logto_client.fetchUserInfo)()
        
        # UserInfoResponse 对象需要用属性访问
        user_id = user_info_obj.sub
        user_email = user_info_obj.email if hasattr(user_info_obj, 'email') else ''
        # 临时方案：直接用邮箱作为显示名称
        user_name = user_email if user_email else '用户'
        
        session['user'] = {
            'id': user_id,
            'name': user_name,      # 现在会显示邮箱地址
            'email': user_email,
        }
        
        # 检查数据库中是否有该用户的设置记录
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM settings WHERE user_id = %s", (user_id,))
        existing = cur.fetchone()
        if not existing:
            cur.execute(
                "INSERT INTO settings (user_id, user_name, student_id) VALUES (%s, %s, %s)",
                (user_id, user_name, '')
            )
            conn.commit()
        cur.close()
        conn.close()
        
        next_url = session.pop('next_url', url_for('index'))
        return redirect(next_url)
    except Exception as e:
        print(f"登录回调出错: {e}")
        return redirect(url_for('index'))

@app.route('/logout')
def logout():
    """登出"""
    session.clear()
    sign_out_uri = async_to_sync(logto_client.signOut)(
        url_for('index', _external=True)
    )
    return redirect(sign_out_uri)
# ===================================

# ========== 登录验证装饰器 ==========
def login_required(f):
    """需要登录才能访问的装饰器"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            session['next_url'] = request.url
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
# ===================================

# ========== 辅助函数（替代原来的 settings_web 中的函数） ==========
def get_user_settings(user_id):
    """获取用户设置"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT user_name, student_id FROM settings WHERE user_id = %s", (user_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    if result:
        return {'user_name': result['user_name'], 'student_id': result['student_id']}
    return {'user_name': '未设置', 'student_id': ''}

def update_user_settings(user_id, user_name, student_id):
    """更新用户设置"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE settings 
        SET user_name = %s, student_id = %s, updated_at = NOW()
        WHERE user_id = %s
    """, (user_name, student_id, user_id))
    conn.commit()
    cur.close()
    conn.close()
# ===================================

# ========== 原有路由 ==========
@app.route('/')
def index():
    """主页面"""
    logged_in_user = session.get('user')
    
    if logged_in_user:
        # 已登录用户，从数据库读取设置
        settings = get_user_settings(logged_in_user['id'])
        user_name = settings['user_name']
        student_id = settings['student_id']
    else:
        # 未登录用户，使用默认值
        user_name = '未设置'
        student_id = ''
    
    return render_template('index.html', 
                         user_name=user_name,
                         student_id=student_id,
                         page='main_menu',
                         logged_in_user=logged_in_user)

@app.route('/word_exam')
@login_required
def word_exam():
    """单词考察页面"""
    exams = [
        {"name": "昔日之光", "color": "#ff6b6b", "route": "past_light"},
        {"name": "圣枪烬临", "color": "#ffa502", "route": "coming_soon"},
        {"name": "意言译语", "color": "#7bed9f", "route": "meaning_language"},
        {"name": "诡影重重", "color": "#70a1ff", "route": "shadow_exam"},
        {"name": "骗子酒馆", "color": "#5352ed", "route": "coming_soon"},
        {"name": "七十二变", "color": "#ff6348", "route": "seventy_two"},
        {"name": "三十六计", "color": "#2ed573", "route": "thirty_six"},
        {"name": "阴影迷踪", "color": "#1e90ff", "route": "shadow_hunter"},
        {"name": "决战之夜", "color": "#e056a0", "route": "final_night"},
        {"name": "万圣之夜", "color": "#ff7f50", "route": "halloween_night"},
        {"name": "流光符印", "color": "#a29bfe", "route": "glowing_card"},
        {"name": "盗宝大师", "color": "#fdcb6e", "route": "treasure_master"}
    ]
    logged_in_user = session.get('user')
    return render_template('index.html', page='word_exam', exams=exams, logged_in_user=logged_in_user)

@app.route('/database_options')
@login_required
def database_options():
    """数据库选项页面"""
    options = [
        {"name": "词汇管理系统", "color": "#00b894", "route": "vocabulary"},
        {"name": "意言译语数据库", "color": "#6c5ce7", "route": "meaning_language_db"},
        {"name": "技能数据库", "color": "#e17055", "route": "skill_db"}
    ]
    logged_in_user = session.get('user')
    return render_template('index.html', page='database_options', options=options, logged_in_user=logged_in_user)

@app.route('/other_projects')
@login_required
def other_projects():
    """其他项目页面"""
    projects = [
        {"name": "汉译英挑战", "color": "#fd79a8", "route": "chinese_to_english"},
        {"name": "噩梦高考", "color": "#636e72", "route": "nightmare_exam"}
    ]
    logged_in_user = session.get('user')
    return render_template('index.html', page='other_projects', projects=projects, logged_in_user=logged_in_user)

@app.route('/exam/<exam_type>')
@login_required
def start_exam(exam_type):
    """启动考试"""
    name_map = {
        'past_light': '昔日之光', 'meaning_language': '意言译语',
        'shadow_exam': '诡影重重', 'seventy_two': '七十二变',
        'thirty_six': '三十六计', 'shadow_hunter': '阴影迷踪',
        'final_night': '决战之夜', 'halloween_night': '万圣之夜',
        'glowing_card': '流光符印', 'treasure_master': '盗宝大师',
        'vocabulary': '词汇管理系统', 'meaning_language_db': '意言译语数据库',
        'skill_db': '技能数据库', 'chinese_to_english': '汉译英挑战',
        'nightmare_exam': '噩梦高考', 'exam_database': '考试数据库',
        'word_recitation': '单词背诵'
    }
    
    if exam_type == 'coming_soon':
        exam_name = name_map.get(exam_type, exam_type)
        return render_template('index.html', page='coming_soon', exam_name=exam_name)
    
    if exam_type == 'vocabulary':
        return redirect(url_for('vocabulary.vocabulary_page'))
    if exam_type == 'word_recitation':
        return redirect(url_for('recitation.recitation_page'))
    if exam_type == 'exam_database':
        return redirect(url_for('exam.exam_database_page'))
    if exam_type == 'past_light':
        return redirect(url_for('past_light.past_light_page'))
    if exam_type == 'shadow_exam':
        return redirect(url_for('shadow.shadow_page'))
    if exam_type == 'seventy_two':
        return redirect(url_for('seventy_two.seventy_two_page'))
    if exam_type == 'thirty_six':
        return redirect(url_for('thirty_six.thirty_six_page'))
    if exam_type == 'treasure_master':
        return redirect(url_for('treasure.treasure_page'))
    if exam_type == 'halloween_night':
        return redirect(url_for('halloween.halloween_page'))
    if exam_type == 'shadow_hunter':
        return redirect(url_for('shadow_hunter.shadow_hunter_page'))
    if exam_type == 'skill_db':                   
        return redirect(url_for('skill_db.skill_db_page')) 
    if exam_type == 'nightmare_exam':
        return redirect(url_for('nightmare.nightmare_page'))
    
    exam_name = name_map.get(exam_type, exam_type)
    logged_in_user = session.get('user')
    return render_template('index.html', page='exam_placeholder', exam_name=exam_name, logged_in_user=logged_in_user)

# ========== 用户设置相关路由 ==========
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def user_settings():
    """用户设置页面"""
    user_id = session['user']['id']
    
    if request.method == 'POST':
        user_name = request.form.get('user_name', '未设置')
        student_id = request.form.get('student_id', '')
        update_user_settings(user_id, user_name, student_id)
        return redirect(url_for('index'))
    
    settings = get_user_settings(user_id)
    return render_template('settings.html', 
                         user_name=settings['user_name'],
                         student_id=settings['student_id'])
# ===================================

if __name__ == '__main__':
    print("英语学习平台网页版启动中...")
    print("请访问: http://127.0.0.1:5000")
    app.run(debug=True, host='127.0.0.1', port=5000)