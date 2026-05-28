# dict_shop_web.py - 词库商城（从商城数据库购买并导入词汇数据库）
from functools import wraps
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from vocabulary_shop_manager import VocabularyManager as ShopManager
from vocabulary_manager import VocabularyManager as VocabManager

dict_shop_bp = Blueprint('dict_shop', __name__)
shop_manager = ShopManager()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            session['next_url'] = request.url
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def get_user_vocab_manager():
    """获取当前用户的词汇管理器"""
    user = session.get('user')
    user_id = user.get('id') if user else None
    return VocabManager(user_id=user_id)


def _owned_dict_names(user_vocab):
    """获取用户已拥有的词典名称"""
    return {d['dict_name'] for d in user_vocab.get_dictionaries_ordered()}


def _import_dictionary(user_vocab, dict_name: str):
    """从商城数据库复制词典到用户词汇数据库"""
    shop_item = shop_manager.get_dictionary_for_shop(dict_name)
    if not shop_item:
        return False, '该词典不存在或已下架'

    if dict_name in _owned_dict_names(user_vocab):
        return False, '您已拥有该词典'

    price = shop_item.get('price', 0) or 0
    if price > 0:
        return False, f'积分不足，需要 {price} 积分（积分系统开发中）'

    # 添加词典
    if not user_vocab.add_dictionary(dict_name, shop_item.get('description', '')):
        return False, '导入失败，请稍后重试'

    # 导入单词组和单词
    groups = shop_manager.get_dictionary_groups_with_words(dict_name)
    total_words = 0
    for group in groups:
        words = group.get('words') or []
        if words:
            user_vocab.add_word_group(
                group['group_name'],
                words,
                group.get('description', ''),
                dict_name,
            )
            total_words += len(words)

    return True, f'成功导入「{dict_name}」：{len(groups)} 个词组，共 {total_words} 个单词'


@dict_shop_bp.route('/dict_shop')
@login_required
def dict_shop_page():
    """词库商城页面"""
    return render_template('dict_shop.html')


@dict_shop_bp.route('/api/dict_shop/list')
@login_required
def list_shop_dicts():
    """商城词典列表"""
    user_vocab = get_user_vocab_manager()
    owned = _owned_dict_names(user_vocab)
    data = []
    for item in shop_manager.get_shop_catalog():
        data.append({
            **item,
            'owned': item['dict_name'] in owned,
        })
    return jsonify({'success': True, 'data': data})


@dict_shop_bp.route('/api/dict_shop/buy', methods=['POST'])
@login_required
def buy_dict():
    """购买（导入）词典到用户词汇数据库"""
    data = request.get_json() or {}
    dict_name = (data.get('dict_name') or '').strip()
    if not dict_name:
        return jsonify({'success': False, 'message': '请选择词典'})

    user_vocab = get_user_vocab_manager()
    success, message = _import_dictionary(user_vocab, dict_name)
    return jsonify({'success': success, 'message': message, 'owned': success})