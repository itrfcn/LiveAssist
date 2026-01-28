from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime
import random
import string
import os
import json
from werkzeug.security import generate_password_hash, check_password_hash
from PIL import Image, ImageDraw, ImageFont
import io

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['WTF_CSRF_TIME_LIMIT'] = None
app.config['WTF_CSRF_ENABLED'] = True
csrf = CSRFProtect(app)
# 配置信任代理，用于在宝塔等反向代理后面获取真实用户IP
app.config['TRAP_HTTP_EXCEPTIONS'] = True
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
socketio = SocketIO(app, cors_allowed_origins="*")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi', 'wmv'}
app.config['RESET_DATABASE_ON_RESTART'] = True  # 控制重启程序是否重置数据库
app.config['CHUNK_UPLOAD_FOLDER'] = 'temp_chunks'  # 分片临时存储目录

db = SQLAlchemy(app)

# 数据库模型
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), unique=True, nullable=False)
    alias = db.Column(db.String(100), default='')
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(255))
    remark = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    messages = db.relationship('Message', backref='user', lazy=True)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('user.user_id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_read = db.Column(db.Boolean, default=False)
    message_type = db.Column(db.String(20), default='text')  # text, image, video
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SystemSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(255), nullable=False)

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class AutoReply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), default='text', nullable=False)  # text, image, video
    order_index = db.Column(db.Integer, default=0, nullable=False)  # 排序索引

class CommonQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), default='text', nullable=False)  # text, image, video
    order_index = db.Column(db.Integer, default=0, nullable=False)  # 排序索引

class WelcomeMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), default='text', nullable=False)  # text, image, video
    order_index = db.Column(db.Integer, default=0, nullable=False)  # 排序索引

# 生成随机用户ID
def generate_user_id():
    return 'user_' + ''.join(random.choices(string.ascii_letters + string.digits, k=10))

# 检查文件扩展名是否允许
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# 生成唯一的文件名
def generate_unique_filename(filename):
    ext = filename.rsplit('.', 1)[1].lower()
    return ''.join(random.choices(string.ascii_letters + string.digits, k=20)) + '.' + ext

# 根据用户代理字符串检测设备类型
def detect_device_type(user_agent):
    if not user_agent:
        return '未知设备'
    
    user_agent = user_agent.lower()
    
    # 移动设备
    if any(device in user_agent for device in ['mobile', 'android', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone']):
        if 'android' in user_agent:
            return 'Android手机'
        elif 'iphone' in user_agent:
            return 'iPhone'
        elif 'ipad' in user_agent:
            return 'iPad'
        else:
            return '移动设备'
    
    # 桌面设备
    elif any(browser in user_agent for browser in ['windows', 'macintosh', 'linux', 'chromeos']):
        if 'windows' in user_agent:
            return 'Windows桌面'
        elif 'macintosh' in user_agent:
            return 'Mac桌面'
        elif 'linux' in user_agent:
            return 'Linux桌面'
        elif 'chromeos' in user_agent:
            return 'Chrome OS'
        else:
            return '桌面设备'
    
    # 其他设备
    else:
        return '其他设备'

# 验证 User Agent 是否正常
def is_valid_user_agent(user_agent):
    if not user_agent:
        return False
    
    user_agent_lower = user_agent.lower()
    
    # 检查是否启用 User Agent 过滤
    if get_system_setting('enable_user_agent_filter') != 'true':
        return True
    
    # 获取被阻止的 User Agent 关键词
    blocked_keywords = get_system_setting('blocked_user_agents', '').split(',')
    
    # 检查是否包含被阻止的关键词
    for keyword in blocked_keywords:
        keyword = keyword.strip().lower()
        if keyword and keyword in user_agent_lower:
            return False
    
    # 检查 User Agent 是否太短（少于10个字符，可能是爬虫）
    if len(user_agent) < 10:
        return False
    
    # 检查是否包含常见的浏览器标识（可选，更严格的验证）
    # 如果 User Agent 不包含任何常见浏览器标识，可能是爬虫
    browser_signatures = ['mozilla', 'webkit', 'gecko', 'chrome', 'safari', 'firefox', 'edge', 'opera', 'trident']
    has_browser_signature = any(sig in user_agent_lower for sig in browser_signatures)
    
    # 如果没有浏览器标识，但也不是空字符串，可能需要更严格的检查
    # 这里我们选择宽松的策略：只要不包含被阻止的关键词，就允许访问
    # 如果需要更严格的验证，可以取消下面的注释
    # if not has_browser_signature:
    #     return False
    
    return True

# 获取系统设置
def get_system_setting(key, default='false'):
    setting = SystemSetting.query.filter_by(key=key).first()
    return setting.value if setting else default

# 更新系统设置
def update_system_setting(key, value):
    setting = SystemSetting.query.filter_by(key=key).first()
    if setting:
        setting.value = value
    else:
        setting = SystemSetting(key=key, value=value)
        db.session.add(setting)
    db.session.commit()

# 初始化数据库
with app.app_context():
    # 检查是否需要重置数据库
    if app.config['RESET_DATABASE_ON_RESTART']:
        # 先删除所有表
        db.drop_all()
        # 重新创建所有表
        db.create_all()
        # 添加默认管理员
        admin = Admin(username='admin', password=generate_password_hash('admin123'))
        db.session.add(admin)
        # 添加默认常见问题
        questions = [
            {'question': '如何注册账号？', 'content': '您可以点击首页的注册按钮，填写相关信息即可注册。', 'message_type': 'text', 'order_index': 0},
            {'question': '如何找回密码？', 'content': '您可以点击登录页面的忘记密码，按照提示操作即可找回。', 'message_type': 'text', 'order_index': 1},
            {'question': '客服工作时间？', 'content': '我们的客服工作时间是周一至周日 9:00-21:00。', 'message_type': 'text', 'order_index': 2}
        ]
        for q in questions:
            cq = CommonQuestion(question=q['question'], content=q['content'], message_type=q['message_type'], order_index=q['order_index'])
            db.session.add(cq)
        # 添加默认关键词自动回复
        auto_replies = [
            {'keyword': '你好', 'content': '你好！请问有什么可以帮助您的？', 'message_type': 'text', 'order_index': 0},
            {'keyword': '谢谢', 'content': '不客气，很高兴为您服务！', 'message_type': 'text', 'order_index': 1},
            {'keyword': '再见', 'content': '再见，祝您生活愉快！', 'message_type': 'text', 'order_index': 2}
        ]
        for ar in auto_replies:
            ar_obj = AutoReply(keyword=ar['keyword'], content=ar['content'], message_type=ar['message_type'], order_index=ar['order_index'])
            db.session.add(ar_obj)
        # 添加默认系统设置
        settings = [
            {'key': 'allow_user_images', 'value': 'true'},
            {'key': 'allow_user_videos', 'value': 'true'},
            {'key': 'chat_path', 'value': '/'},
            {'key': 'enable_user_agent_filter', 'value': 'false'},
            {'key': 'blocked_user_agents', 'value': 'bot,crawler,spider,scraper,python-requests,curl,wget'}
        ]
        for setting in settings:
            ss = SystemSetting(key=setting['key'], value=setting['value'])
            db.session.add(ss)
        
        # 添加默认打招呼语句
        welcome_messages = [
            {'content': '您好！欢迎使用我们的客服系统，请问有什么可以帮助您的？', 'message_type': 'text', 'order_index': 0},
            {'content': '我们的工作时间是周一至周日 9:00-21:00', 'message_type': 'text', 'order_index': 1}
        ]
        for msg in welcome_messages:
            wm = WelcomeMessage(content=msg['content'], message_type=msg['message_type'], order_index=msg['order_index'])
            db.session.add(wm)
        
        db.session.commit()
    else:
        # 只创建表，不删除已有数据
        db.create_all()
    
    # 创建分片上传临时目录
    if not os.path.exists(app.config['CHUNK_UPLOAD_FOLDER']):
        os.makedirs(app.config['CHUNK_UPLOAD_FOLDER'])

# 路由
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/')
def index():
    # 获取聊天路径设置
    chat_path = get_system_setting('chat_path', '/')
    # 如果设置了自定义路径，根路径返回404
    if chat_path != '/':
        return 'Not Found', 404
    
    # 验证 User Agent
    user_agent = request.headers.get('User-Agent', '')
    if not is_valid_user_agent(user_agent):
        return 'Access Denied: Invalid User Agent', 403
    
    # 生成或获取用户ID
    if 'user_id' not in session:
        session['user_id'] = generate_user_id()
    user_id = session['user_id']
    
    # 记录用户信息
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        user = User(
            user_id=user_id,
            ip_address=request.remote_addr,
            user_agent=user_agent
        )
        db.session.add(user)
        db.session.commit()
        
        # 用户首次访问，发送打招呼语句
        welcome_messages = WelcomeMessage.query.order_by(WelcomeMessage.order_index).all()
        for msg in welcome_messages:
            welcome_message = Message(
                user_id=user_id,
                content=msg.content,
                is_admin=True,
                message_type=msg.message_type
            )
            db.session.add(welcome_message)
        db.session.commit()
    
    # 获取常见问题
    common_questions = CommonQuestion.query.all()
    # 转换为字典列表
    common_questions_list = [{'id': cq.id, 'question': cq.question, 'answer': cq.content} for cq in common_questions]
    
    # 获取系统设置
    allow_images = get_system_setting('allow_user_images') == 'true'
    allow_videos = get_system_setting('allow_user_videos') == 'true'
    
    return render_template('index.html', user_id=user_id, common_questions=common_questions_list, 
                           allow_images=allow_images, allow_videos=allow_videos)

@app.route('/<path:path>')
def custom_path(path):
    # 获取聊天路径设置
    chat_path = get_system_setting('chat_path', '/')
    # 如果当前路径不匹配自定义路径设置，返回404
    if chat_path == '/' or '/' + path != chat_path:
        return 'Not Found', 404
    
    # 生成或获取用户ID
    if 'user_id' not in session:
        session['user_id'] = generate_user_id()
    user_id = session['user_id']
    
    # 记录用户信息
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        user = User(
            user_id=user_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(user)
        db.session.commit()
        
        # 用户首次访问，发送打招呼语句
        welcome_messages = WelcomeMessage.query.order_by(WelcomeMessage.order_index).all()
        for msg in welcome_messages:
            welcome_message = Message(
                user_id=user_id,
                content=msg.content,
                is_admin=True,
                message_type=msg.message_type
            )
            db.session.add(welcome_message)
        db.session.commit()
    
    # 获取常见问题
    common_questions = CommonQuestion.query.all()
    # 转换为字典列表
    common_questions_list = [{'id': cq.id, 'question': cq.question, 'answer': cq.content} for cq in common_questions]
    
    # 获取系统设置
    allow_images = get_system_setting('allow_user_images') == 'true'
    allow_videos = get_system_setting('allow_user_videos') == 'true'
    
    return render_template('index.html', user_id=user_id, common_questions=common_questions_list, 
                           allow_images=allow_images, allow_videos=allow_videos)

@app.route('/get_messages', methods=['POST'])
@csrf.exempt
def get_messages():
    user_id = request.json.get('user_id')
    messages = Message.query.filter_by(user_id=user_id).order_by(Message.created_at).all()
    return jsonify([{
        'content': msg.content,
        'is_admin': msg.is_admin,
        'message_type': msg.message_type,
        'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
    } for msg in messages])



@app.route('/admin')
def admin_login():
    if 'admin_logged_in' in session and session['admin_logged_in']:
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_login.html')

@app.route('/admin/login', methods=['POST'])
def admin_login_post():
    username = request.form.get('username')
    password = request.form.get('password')
    captcha = request.form.get('captcha')
    
    # 验证验证码
    if not captcha or captcha.upper() != session.get('captcha', '').upper():
        return redirect(url_for('admin_login'))
    
    admin = Admin.query.filter_by(username=username).first()
    if admin and check_password_hash(admin.password, password):
        session['admin_logged_in'] = True
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('admin_login'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        return redirect(url_for('admin_login'))
    
    # 获取所有用户
    users = User.query.all()
    
    # 为每个用户计算未读消息数量、设备类型和最新消息时间
    user_data = []
    for user in users:
        unread_count = Message.query.filter_by(user_id=user.user_id, is_admin=False, is_read=False).count()
        device_type = detect_device_type(user.user_agent)
        # 获取最新消息时间
        latest_message = Message.query.filter_by(user_id=user.user_id).order_by(Message.created_at.desc()).first()
        latest_message_time = latest_message.created_at if latest_message else user.created_at
        
        user_data.append({
            'user': user,
            'unread_count': unread_count,
            'device_type': device_type,
            'latest_message_time': latest_message_time
        })
    
    # 按最新消息时间排序，最新的在上面
    user_data.sort(key=lambda x: x['latest_message_time'], reverse=True)
    
    return render_template('admin_dashboard.html', user_data=user_data)

@app.route('/admin/dashboard_data')
def admin_dashboard_data():
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        return jsonify([])
    
    # 获取所有用户
    users = User.query.all()
    user_data = []
    
    for user in users:
        # 计算未读消息数
        unread_count = Message.query.filter_by(user_id=user.user_id, is_admin=False, is_read=False).count()
        # 检测设备类型
        device_type = detect_device_type(user.user_agent)
        # 获取最新消息时间
        latest_message = Message.query.filter_by(user_id=user.user_id).order_by(Message.created_at.desc()).first()
        latest_message_time = latest_message.created_at if latest_message else user.created_at
        
        user_data.append({
            'user': {
                'user_id': user.user_id,
                'alias': user.alias,
                'ip_address': user.ip_address,
                'user_agent': user.user_agent,
                'device_type': device_type,
                'remark': user.remark,
                'created_at': user.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'latest_message_time': latest_message_time.strftime('%Y-%m-%d %H:%M:%S')
            },
            'unread_count': unread_count
        })
    
    # 按最新消息时间排序，最新的在上面
    user_data.sort(key=lambda x: x['user']['latest_message_time'], reverse=True)
    
    return jsonify(user_data)

@app.route('/admin/chat/<user_id>')
def admin_chat(user_id):
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        return redirect(url_for('admin_login'))
    
    # 获取用户的所有消息
    messages = Message.query.filter_by(user_id=user_id).order_by(Message.created_at).all()
    
    # 将用户消息标记为已读
    for msg in messages:
        if not msg.is_admin and not msg.is_read:
            msg.is_read = True
            db.session.commit()
    
    return render_template('admin_chat.html', user_id=user_id, messages=messages)



@app.route('/admin/auto_replies')
def admin_auto_replies():
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        return redirect(url_for('admin_login'))
    
    auto_replies = AutoReply.query.all()
    return render_template('admin_auto_replies.html', auto_replies=auto_replies)

@app.route('/admin/add_auto_reply', methods=['POST'])
def add_auto_reply():
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        return jsonify({'status': 'error'})
    
    keyword = request.json.get('keyword')
    content = request.json.get('content')
    message_type = request.json.get('message_type', 'text')
    order_index = request.json.get('order_index', 0)
    
    auto_reply = AutoReply(keyword=keyword, content=content, message_type=message_type, order_index=order_index)
    db.session.add(auto_reply)
    db.session.commit()
    
    return jsonify({'status': 'success'})

@app.route('/admin/delete_auto_reply/<int:id>')
def delete_auto_reply(id):
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        return redirect(url_for('admin_login'))
    
    auto_reply = AutoReply.query.get(id)
    if auto_reply:
        db.session.delete(auto_reply)
        db.session.commit()
    
    return redirect(url_for('admin_auto_replies'))

@app.route('/admin/common_questions')
def admin_common_questions():
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        return redirect(url_for('admin_login'))
    
    common_questions = CommonQuestion.query.all()
    return render_template('admin_common_questions.html', common_questions=common_questions)

@app.route('/admin/add_common_question', methods=['POST'])
def add_common_question():
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        return jsonify({'status': 'error'})
    
    question = request.json.get('question')
    content = request.json.get('content')
    message_type = request.json.get('message_type', 'text')
    order_index = request.json.get('order_index', 0)
    
    cq = CommonQuestion(question=question, content=content, message_type=message_type, order_index=order_index)
    db.session.add(cq)
    db.session.commit()
    
    return jsonify({'status': 'success'})

@app.route('/upload', methods=['POST'])
def upload_file():
    # 验证 User Agent
    user_agent = request.headers.get('User-Agent', '')
    if not is_valid_user_agent(user_agent):
        return jsonify({'status': 'error', 'message': 'Access Denied: Invalid User Agent'}), 403
    
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'})
    
    if file and allowed_file(file.filename):
        # 检查用户是否可以上传文件
        allow_images = get_system_setting('allow_user_images') == 'true'
        allow_videos = get_system_setting('allow_user_videos') == 'true'
        
        # 检查文件类型
        ext = file.filename.rsplit('.', 1)[1].lower()
        if (ext in ['png', 'jpg', 'jpeg', 'gif'] and not allow_images) or \
           (ext in ['mp4', 'mov', 'avi', 'wmv'] and not allow_videos):
            return jsonify({'status': 'error', 'message': 'File type not allowed'})
        
        # 生成唯一文件名
        filename = generate_unique_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # 确定消息类型
        message_type = 'image' if ext in ['png', 'jpg', 'jpeg', 'gif'] else 'video'
        
        return jsonify({'status': 'success', 'filename': filename, 'message_type': message_type})
    
    return jsonify({'status': 'error', 'message': 'File type not allowed'})

@app.route('/upload_chunk', methods=['POST'])
@csrf.exempt
def upload_chunk():
    # 验证 User Agent
    user_agent = request.headers.get('User-Agent', '')
    if not is_valid_user_agent(user_agent):
        return jsonify({'status': 'error', 'message': 'Access Denied: Invalid User Agent'}), 403
    
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part'})
    
    file = request.files['file']
    file_id = request.form.get('fileId')
    chunk_index = int(request.form.get('chunkIndex'))
    total_chunks = int(request.form.get('totalChunks'))
    file_name = request.form.get('fileName')
    
    if not file_id or not file_name:
        return jsonify({'status': 'error', 'message': 'Missing required parameters'})
    
    # 创建临时分片目录
    chunk_dir = os.path.join(app.config['CHUNK_UPLOAD_FOLDER'], file_id)
    if not os.path.exists(chunk_dir):
        os.makedirs(chunk_dir)
    
    # 保存分片
    chunk_filename = f"chunk_{chunk_index}"
    chunk_path = os.path.join(chunk_dir, chunk_filename)
    file.save(chunk_path)
    
    # 保存元数据
    metadata = {
        'fileId': file_id,
        'fileName': file_name,
        'fileSize': request.form.get('fileSize'),
        'fileType': request.form.get('fileType'),
        'totalChunks': total_chunks,
        'uploadedChunks': len([f for f in os.listdir(chunk_dir) if f.startswith('chunk_')])
    }
    
    metadata_path = os.path.join(chunk_dir, 'metadata.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f)
    
    return jsonify({'status': 'success', 'chunkIndex': chunk_index})

@app.route('/merge_chunks', methods=['POST'])
@csrf.exempt
def merge_chunks():
    # 验证 User Agent
    user_agent = request.headers.get('User-Agent', '')
    if not is_valid_user_agent(user_agent):
        return jsonify({'status': 'error', 'message': 'Access Denied: Invalid User Agent'}), 403
    
    data = request.json
    file_id = data.get('fileId')
    total_chunks = data.get('totalChunks')
    file_name = data.get('fileName')
    file_type = data.get('fileType')
    
    if not file_id or not total_chunks or not file_name:
        return jsonify({'status': 'error', 'message': 'Missing required parameters'})
    
    chunk_dir = os.path.join(app.config['CHUNK_UPLOAD_FOLDER'], file_id)
    
    # 检查所有分片是否都已上传
    uploaded_chunks = len([f for f in os.listdir(chunk_dir) if f.startswith('chunk_')])
    if uploaded_chunks != total_chunks:
        return jsonify({'status': 'error', 'message': f'Not all chunks uploaded ({uploaded_chunks}/{total_chunks})'})
    
    # 检查文件类型是否允许
    ext = file_name.rsplit('.', 1)[1].lower()
    if not allowed_file(file_name):
        return jsonify({'status': 'error', 'message': 'File type not allowed'})
    
    # 检查用户是否可以上传文件
    allow_images = get_system_setting('allow_user_images') == 'true'
    allow_videos = get_system_setting('allow_user_videos') == 'true'
    
    if (ext in ['png', 'jpg', 'jpeg', 'gif'] and not allow_images) or \
       (ext in ['mp4', 'mov', 'avi', 'wmv'] and not allow_videos):
        return jsonify({'status': 'error', 'message': 'File type not allowed'})
    
    # 生成最终文件名
    final_filename = generate_unique_filename(file_name)
    final_path = os.path.join(app.config['UPLOAD_FOLDER'], final_filename)
    
    # 合并分片
    try:
        with open(final_path, 'wb') as outfile:
            for i in range(total_chunks):
                chunk_path = os.path.join(chunk_dir, f'chunk_{i}')
                with open(chunk_path, 'rb') as infile:
                    outfile.write(infile.read())
        
        # 清理临时分片
        import shutil
        shutil.rmtree(chunk_dir)
        
        # 确定消息类型
        message_type = 'image' if ext in ['png', 'jpg', 'jpeg', 'gif'] else 'video'
        
        return jsonify({'status': 'success', 'filename': final_filename, 'message_type': message_type})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Merge failed: {str(e)}'})

@app.route('/check_upload_status', methods=['POST'])
@csrf.exempt
def check_upload_status():
    # 验证 User Agent
    user_agent = request.headers.get('User-Agent', '')
    if not is_valid_user_agent(user_agent):
        return jsonify({'status': 'error', 'message': 'Access Denied: Invalid User Agent'}), 403
    
    data = request.json
    file_id = data.get('fileId')
    
    if not file_id:
        return jsonify({'status': 'error', 'message': 'Missing file ID'})
    
    chunk_dir = os.path.join(app.config['CHUNK_UPLOAD_FOLDER'], file_id)
    
    if not os.path.exists(chunk_dir):
        return jsonify({'status': 'not_found', 'uploadedChunks': 0})
    
    metadata_path = os.path.join(chunk_dir, 'metadata.json')
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        return jsonify({'status': 'success', **metadata})
    else:
        uploaded_chunks = len([f for f in os.listdir(chunk_dir) if f.startswith('chunk_')])
        return jsonify({'status': 'success', 'uploadedChunks': uploaded_chunks})

@app.route('/delete_chunks', methods=['POST'])
@csrf.exempt
def delete_chunks():
    # 验证 User Agent
    user_agent = request.headers.get('User-Agent', '')
    if not is_valid_user_agent(user_agent):
        return jsonify({'status': 'error', 'message': 'Access Denied: Invalid User Agent'}), 403
    
    data = request.json
    file_id = data.get('fileId')
    
    if not file_id:
        return jsonify({'status': 'error', 'message': 'Missing file ID'})
    
    chunk_dir = os.path.join(app.config['CHUNK_UPLOAD_FOLDER'], file_id)
    
    if os.path.exists(chunk_dir):
        import shutil
        shutil.rmtree(chunk_dir)
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'error', 'message': 'Chunks not found'})

@app.route('/admin/upload', methods=['POST'])
def admin_upload_file():
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        return jsonify({'status': 'error', 'message': 'Unauthorized'})
    
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'})
    
    if file and allowed_file(file.filename):
        # 生成唯一文件名
        filename = generate_unique_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # 确定消息类型
        ext = file.filename.rsplit('.', 1)[1].lower()
        message_type = 'image' if ext in ['png', 'jpg', 'jpeg', 'gif'] else 'video'
        
        return jsonify({'status': 'success', 'filename': filename, 'message_type': message_type})
    
    return jsonify({'status': 'error', 'message': 'File type not allowed'})

@app.route('/admin/upload_chunk', methods=['POST'])
@csrf.exempt
def admin_upload_chunk():
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        return jsonify({'status': 'error', 'message': 'Unauthorized'})
    
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part'})
    
    file = request.files['file']
    file_id = request.form.get('fileId')
    chunk_index = int(request.form.get('chunkIndex'))
    total_chunks = int(request.form.get('totalChunks'))
    file_name = request.form.get('fileName')
    
    if not file_id or not file_name:
        return jsonify({'status': 'error', 'message': 'Missing required parameters'})
    
    # 创建临时分片目录
    chunk_dir = os.path.join(app.config['CHUNK_UPLOAD_FOLDER'], file_id)
    if not os.path.exists(chunk_dir):
        os.makedirs(chunk_dir)
    
    # 保存分片
    chunk_filename = f"chunk_{chunk_index}"
    chunk_path = os.path.join(chunk_dir, chunk_filename)
    file.save(chunk_path)
    
    # 保存元数据
    metadata = {
        'fileId': file_id,
        'fileName': file_name,
        'fileSize': request.form.get('fileSize'),
        'fileType': request.form.get('fileType'),
        'totalChunks': total_chunks,
        'uploadedChunks': len([f for f in os.listdir(chunk_dir) if f.startswith('chunk_')])
    }
    
    metadata_path = os.path.join(chunk_dir, 'metadata.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f)
    
    return jsonify({'status': 'success', 'chunkIndex': chunk_index})

@app.route('/admin/merge_chunks', methods=['POST'])
@csrf.exempt
def admin_merge_chunks():
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        return jsonify({'status': 'error', 'message': 'Unauthorized'})
    
    data = request.json
    file_id = data.get('fileId')
    total_chunks = data.get('totalChunks')
    file_name = data.get('fileName')
    file_type = data.get('fileType')
    
    if not file_id or not total_chunks or not file_name:
        return jsonify({'status': 'error', 'message': 'Missing required parameters'})
    
    chunk_dir = os.path.join(app.config['CHUNK_UPLOAD_FOLDER'], file_id)
    
    # 检查所有分片是否都已上传
    uploaded_chunks = len([f for f in os.listdir(chunk_dir) if f.startswith('chunk_')])
    if uploaded_chunks != total_chunks:
        return jsonify({'status': 'error', 'message': f'Not all chunks uploaded ({uploaded_chunks}/{total_chunks})'})
    
    # 检查文件类型是否允许
    if not allowed_file(file_name):
        return jsonify({'status': 'error', 'message': 'File type not allowed'})
    
    # 生成最终文件名
    final_filename = generate_unique_filename(file_name)
    final_path = os.path.join(app.config['UPLOAD_FOLDER'], final_filename)
    
    # 合并分片
    try:
        with open(final_path, 'wb') as outfile:
            for i in range(total_chunks):
                chunk_path = os.path.join(chunk_dir, f'chunk_{i}')
                with open(chunk_path, 'rb') as infile:
                    outfile.write(infile.read())
        
        # 清理临时分片
        import shutil
        shutil.rmtree(chunk_dir)
        
        # 确定消息类型
        ext = file_name.rsplit('.', 1)[1].lower()
        message_type = 'image' if ext in ['png', 'jpg', 'jpeg', 'gif'] else 'video'
        
        return jsonify({'status': 'success', 'filename': final_filename, 'message_type': message_type})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Merge failed: {str(e)}'})

@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        return redirect(url_for('admin_login'))
    
    success_message = None
    
    if request.method == 'POST':
        # 保存设置
        allow_user_images = 'allow_user_images' in request.form
        allow_user_videos = 'allow_user_videos' in request.form
        chat_path = request.form.get('chat_path', '/')
        enable_user_agent_filter = 'enable_user_agent_filter' in request.form
        blocked_user_agents = request.form.get('blocked_user_agents', 'bot,crawler,spider,scraper,python-requests,curl,wget')
        
        # 更新或添加系统设置
        update_system_setting('allow_user_images', 'true' if allow_user_images else 'false')
        update_system_setting('allow_user_videos', 'true' if allow_user_videos else 'false')
        update_system_setting('chat_path', chat_path)
        update_system_setting('enable_user_agent_filter', 'true' if enable_user_agent_filter else 'false')
        update_system_setting('blocked_user_agents', blocked_user_agents)
        
        success_message = '设置保存成功！'
    
    # 获取当前设置
    allow_user_images = get_system_setting('allow_user_images') == 'true'
    allow_user_videos = get_system_setting('allow_user_videos') == 'true'
    chat_path = get_system_setting('chat_path', '/')
    enable_user_agent_filter = get_system_setting('enable_user_agent_filter') == 'true'
    blocked_user_agents = get_system_setting('blocked_user_agents', 'bot,crawler,spider,scraper,python-requests,curl,wget')
    
    return render_template('admin_settings.html', 
                         allow_user_images=allow_user_images, 
                         allow_user_videos=allow_user_videos,
                         chat_path=chat_path,
                         enable_user_agent_filter=enable_user_agent_filter,
                         blocked_user_agents=blocked_user_agents,
                         success_message=success_message)

@app.route('/admin/change_password', methods=['POST'])
def change_password():
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        return redirect(url_for('admin_login'))
    
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # 获取管理员账户
    admin = Admin.query.first()
    if not admin:
        return redirect(url_for('admin_settings'))
    
    # 验证当前密码
    if not check_password_hash(admin.password, current_password):
        return render_template('admin_settings.html', 
                             allow_user_images=get_system_setting('allow_user_images') == 'true', 
                             allow_user_videos=get_system_setting('allow_user_videos') == 'true',
                             success_message='当前密码错误！')
    
    # 验证新密码和确认密码
    if new_password != confirm_password:
        return render_template('admin_settings.html', 
                             allow_user_images=get_system_setting('allow_user_images') == 'true', 
                             allow_user_videos=get_system_setting('allow_user_videos') == 'true',
                             success_message='新密码和确认密码不一致！')
    
    # 更新密码
    admin.password = generate_password_hash(new_password)
    db.session.commit()
    
    return render_template('admin_settings.html', 
                         allow_user_images=get_system_setting('allow_user_images') == 'true', 
                         allow_user_videos=get_system_setting('allow_user_videos') == 'true',
                         success_message='密码修改成功！')

@app.route('/admin/welcome_messages', methods=['GET', 'POST'])
def admin_welcome_messages():
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        return redirect('/admin')
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            message_type = request.form.get('message_type')
            order_index = request.form.get('order_index', 0, type=int)
            
            if message_type == 'text':
                content = request.form.get('content')
                if content:
                    welcome_message = WelcomeMessage(
                        content=content,
                        message_type=message_type,
                        order_index=order_index
                    )
                    db.session.add(welcome_message)
                    db.session.commit()
            else:
                # 处理图片和视频 - 使用分片上传的文件名
                uploaded_filename = request.form.get('uploaded_filename')
                if uploaded_filename and allowed_file(uploaded_filename):
                    welcome_message = WelcomeMessage(
                        content=uploaded_filename,
                        message_type=message_type,
                        order_index=order_index
                    )
                    db.session.add(welcome_message)
                    db.session.commit()
    
    # 获取所有打招呼语句，按排序索引排序
    welcome_messages = WelcomeMessage.query.order_by(WelcomeMessage.order_index).all()
    
    return render_template('admin_welcome_messages.html', welcome_messages=welcome_messages)

@app.route('/admin/delete_welcome_message/<id>')
def delete_welcome_message(id):
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        return redirect('/admin')
    
    welcome_message = WelcomeMessage.query.get(id)
    if welcome_message:
        # 如果是图片或视频，删除文件
        if welcome_message.message_type in ['image', 'video']:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], welcome_message.content)
            if os.path.exists(filepath):
                os.remove(filepath)
        
        db.session.delete(welcome_message)
        db.session.commit()
    
    return redirect('/admin/welcome_messages')

@app.route('/admin/update_setting', methods=['POST'])
@csrf.exempt
def update_setting():
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        return jsonify({'status': 'error', 'message': 'Unauthorized'})
    
    key = request.json.get('key')
    value = request.json.get('value')
    
    setting = SystemSetting.query.filter_by(key=key).first()
    if setting:
        setting.value = value
        db.session.commit()
        return jsonify({'status': 'success'})
    
    return jsonify({'status': 'error', 'message': 'Setting not found'})

@app.route('/admin/delete_common_question/<int:id>')
def delete_common_question(id):
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        return redirect(url_for('admin_login'))
    
    cq = CommonQuestion.query.get(id)
    if cq:
        db.session.delete(cq)
        db.session.commit()
    
    return redirect(url_for('admin_common_questions'))

@app.route('/admin/delete_user/<string:user_id>')
def delete_user(user_id):
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        return redirect(url_for('admin_login'))
    
    # 删除用户的所有消息
    messages = Message.query.filter_by(user_id=user_id).all()
    for message in messages:
        db.session.delete(message)
    
    # 删除用户记录
    user = User.query.filter_by(user_id=user_id).first()
    if user:
        db.session.delete(user)
    
    db.session.commit()
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/update_user_info', methods=['POST'])
def update_user_info():
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        return jsonify({'status': 'error'})
    
    user_id = request.json.get('user_id')
    alias = request.json.get('alias', '')
    remark = request.json.get('remark', '')
    
    # 查找用户
    user = User.query.filter_by(user_id=user_id).first()
    if user:
        # 更新用户信息
        user.alias = alias
        user.remark = remark
        db.session.commit()
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'error', 'message': 'User not found'})

# 生成验证码
@app.route('/admin/captcha')
def generate_captcha():
    # 生成随机验证码
    captcha_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    
    # 存储验证码到session
    session['captcha'] = captcha_text
    
    # 创建验证码图像
    width, height = 120, 40
    image = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # 尝试使用系统字体，如果失败则使用默认字体
    try:
        font = ImageFont.truetype('arial.ttf', 28)
    except:
        font = ImageFont.load_default()
    
    # 绘制验证码文本
    for i, char in enumerate(captcha_text):
        draw.text((20 + i * 25, 5), char, fill=(random.randint(0, 100), random.randint(0, 100), random.randint(0, 100)), font=font)
    
    # 添加干扰线
    for _ in range(5):
        draw.line([(random.randint(0, width), random.randint(0, height)), (random.randint(0, width), random.randint(0, height))], fill=(random.randint(0, 200), random.randint(0, 200), random.randint(0, 200)), width=1)
    
    # 添加干扰点
    for _ in range(50):
        draw.point([(random.randint(0, width), random.randint(0, height))], fill=(random.randint(0, 200), random.randint(0, 200), random.randint(0, 200)))
    
    # 将图像转换为响应
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    buffer.seek(0)
    
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'image/png'
    return response

# WebSocket事件处理
@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('join_room')
def handle_join_room(data):
    user_id = data['user_id']
    join_room(user_id)
    print(f'User {user_id} joined room')

@socketio.on('join_admin_room')
def handle_join_admin_room():
    join_room('admin')
    print('Admin joined admin room')

@socketio.on('send_message')
def handle_send_message(data):
    user_id = data['user_id']
    content = data['content']
    message_type = data.get('message_type', 'text')
    is_admin = data.get('is_admin', False)
    
    # 保存消息到数据库
    message = Message(
        user_id=user_id,
        content=content,
        is_admin=is_admin,
        message_type=message_type
    )
    db.session.add(message)
    db.session.commit()
    
    # 发送消息到房间
    socketio.emit('new_message', {
        'content': content,
        'is_admin': is_admin,
        'message_type': message_type,
        'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S')
    }, room=user_id)
    
    # 通知管理员更新用户列表
    notify_admin_update()
    
    # 如果是用户消息，检查自动回复
    if not is_admin and message_type == 'text':
        # 检查关键词自动回复
        auto_replies = AutoReply.query.order_by(AutoReply.order_index).all()
        reply_sent = False
        
        # 先检查常见问题匹配
        common_questions = CommonQuestion.query.order_by(CommonQuestion.order_index).all()
        for cq in common_questions:
            if cq.question == content:
                admin_reply = Message(
                    user_id=user_id,
                    content=cq.content,
                    is_admin=True,
                    message_type=cq.message_type
                )
                db.session.add(admin_reply)
                db.session.commit()
                
                # 发送自动回复到房间
                socketio.emit('new_message', {
                    'content': cq.content,
                    'is_admin': True,
                    'message_type': cq.message_type,
                    'created_at': admin_reply.created_at.strftime('%Y-%m-%d %H:%M:%S')
                }, room=user_id)
                reply_sent = True
                break
        
        # 如果没有匹配常见问题，检查关键词自动回复
        if not reply_sent:
            for reply in auto_replies:
                if reply.keyword in content:
                    admin_reply = Message(
                        user_id=user_id,
                        content=reply.content,
                        is_admin=True,
                        message_type=reply.message_type
                    )
                    db.session.add(admin_reply)
                    db.session.commit()
                    
                    # 发送自动回复到房间
                    socketio.emit('new_message', {
                        'content': reply.content,
                        'is_admin': True,
                        'message_type': reply.message_type,
                        'created_at': admin_reply.created_at.strftime('%Y-%m-%d %H:%M:%S')
                    }, room=user_id)
                    break

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

# 修改现有的发送消息函数，添加WebSocket通知
def send_message_with_notification(user_id, content, message_type='text', is_admin=False):
    message = Message(
        user_id=user_id,
        content=content,
        is_admin=is_admin,
        message_type=message_type
    )
    db.session.add(message)
    db.session.commit()
    
    # 通过WebSocket发送消息
    socketio.emit('new_message', {
        'content': content,
        'is_admin': is_admin,
        'message_type': message_type,
        'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S')
    }, room=user_id)
    
    # 通知管理员更新用户列表
    notify_admin_update()
    
    return message

# 通知管理员更新用户列表
def notify_admin_update():
    socketio.emit('admin_update', {}, room='admin')

# 修改admin_send_message函数，使用WebSocket通知
@app.route('/admin/send_message', methods=['POST'])
@csrf.exempt
def admin_send_message():
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        return jsonify({'status': 'error'})
    
    user_id = request.json.get('user_id')
    content = request.json.get('content')
    message_type = request.json.get('message_type', 'text')
    
    # 使用新函数发送消息并通知
    send_message_with_notification(user_id, content, message_type, is_admin=True)
    
    return jsonify({'status': 'success'})

# 修改send_message函数，使用WebSocket通知
@app.route('/send_message', methods=['POST'])
@csrf.exempt
def send_message():
    # 验证 User Agent
    user_agent = request.headers.get('User-Agent', '')
    if not is_valid_user_agent(user_agent):
        return jsonify({'status': 'error', 'message': 'Access Denied: Invalid User Agent'}), 403
    
    user_id = request.json.get('user_id')
    content = request.json.get('content')
    message_type = request.json.get('message_type', 'text')
    
    # 使用新函数发送消息并通知
    message = send_message_with_notification(user_id, content, message_type, is_admin=False)
    
    return jsonify({'status': 'success'})

@app.errorhandler(404)
def not_found_error(error):
    return 'Not Found', 404

@app.errorhandler(403)
def forbidden_error(error):
    return 'Access Denied', 403

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return 'Internal Server Error', 500

if __name__ == '__main__':
    socketio.run(app, debug=True)