# 在线客服系统项目文档

## 1. 项目概述

### 1.1 项目简介
在线客服系统是一个基于Flask框架开发的Web应用，提供用户与客服人员之间的实时消息交互功能。系统支持文本消息、图片和视频的发送与接收，以及关键词自动回复、常见问题快速选择等功能，为用户提供便捷的在线咨询服务。

### 1.2 主要功能

#### 用户端功能
- 在线聊天：支持文本消息的发送与接收
- 文件上传：支持上传图片和视频文件
- 常见问题：提供常见问题快速选择
- 消息格式化：支持消息文本的加粗、颜色设置
- 链接处理：自动识别并添加点击复制功能

#### 管理员端功能
- 用户管理：查看、管理所有用户的聊天记录
- 消息回复：回复用户消息，支持文本、图片、视频
- 关键词自动回复：设置关键词及其对应的自动回复内容
- 常见问题设置：管理常见问题及其答案
- 打招呼语句设置：设置用户首次访问时的欢迎消息
- 系统设置：管理用户文件上传权限
- 密码修改：修改管理员密码

## 2. 技术架构

### 2.1 技术栈

| 类别 | 技术/框架 | 版本 | 用途 |
|------|-----------|------|------|
| 后端 | Flask | 最新版 | Web框架，处理HTTP请求 |
| 后端 | SQLAlchemy | 最新版 | ORM框架，处理数据库操作 |
| 后端 | SQLite | 内置 | 轻量级数据库，存储系统数据 |
| 前端 | HTML5 | 最新版 | 页面结构 |
| 前端 | CSS3 | 最新版 | 页面样式 |
| 前端 | JavaScript | ES6+ | 前端交互逻辑 |
| 安全 | Werkzeug | 最新版 | 密码哈希、安全工具 |

### 2.2 系统架构

系统采用典型的MVC架构模式：

- **Model**：数据模型层，定义数据库表结构
- **View**：视图层，负责页面渲染
- **Controller**：控制器层，处理业务逻辑和请求分发

### 2.3 数据库设计

#### 核心数据表

| 表名 | 描述 | 主要字段 |
|------|------|----------|
| User | 用户信息表 | id, user_id, alias, ip_address, user_agent, remark, created_at |
| Message | 消息表 | id, user_id, content, is_admin, is_read, message_type, created_at |
| Admin | 管理员表 | id, username, password |
| AutoReply | 关键词自动回复表 | id, keyword, content, message_type, order_index |
| CommonQuestion | 常见问题表 | id, question, content, message_type, order_index |
| WelcomeMessage | 打招呼语句表 | id, content, message_type, order_index |
| SystemSetting | 系统设置表 | id, key, value |

## 3. 项目结构

```
/
├── app.py                # 主应用文件，包含所有路由和业务逻辑
├── templates/            # HTML模板目录
│   ├── index.html        # 用户端聊天页面
│   ├── admin_login.html  # 管理员登录页面
│   ├── admin_dashboard.html  # 管理员控制台
│   ├── admin_chat.html   # 管理员聊天页面
│   ├── admin_auto_replies.html  # 关键词自动回复设置
│   ├── admin_common_questions.html  # 常见问题设置
│   ├── admin_welcome_messages.html  # 打招呼语句设置
│   └── admin_settings.html  # 系统设置
├── uploads/              # 文件上传目录
├── instance/             # 数据库文件目录
│   └── chat.db           # SQLite数据库文件
└── 项目文档.md            # 项目文档
```

## 4. 核心功能模块

### 4.1 用户管理模块

- **用户标识**：系统自动为每个用户生成唯一的user_id
- **用户信息**：记录用户的IP地址、浏览器信息、设备类型等
- **用户备注**：管理员可以为用户添加别名和备注信息
- **消息管理**：记录用户与管理员之间的所有消息

### 4.2 消息处理模块

- **消息类型**：支持文本、图片、视频三种消息类型
- **消息发送**：用户和管理员都可以发送消息
- **消息接收**：实时接收对方发送的消息
- **消息状态**：标记消息的已读/未读状态
- **消息格式化**：支持消息文本的加粗、颜色设置

### 4.3 自动回复模块

- **关键词匹配**：根据用户发送的消息内容匹配关键词
- **自动回复**：匹配成功后自动发送预设的回复内容
- **常见问题**：用户可以直接点击常见问题获取答案
- **打招呼语句**：用户首次访问时自动发送欢迎消息

### 4.4 文件上传模块

- **文件类型**：支持图片（png, jpg, jpeg, gif）和视频（mp4, mov, avi, wmv）
- **文件验证**：验证文件类型和大小
- **文件存储**：将文件存储到uploads目录
- **文件访问**：通过URL访问上传的文件

### 4.5 系统设置模块

- **文件上传权限**：控制用户是否可以上传图片和视频
- **管理员密码**：修改管理员登录密码
- **数据库重置**：控制重启程序是否重置数据库

## 5. 安全措施

### 5.1 后端安全

- **密码安全**：使用Werkzeug的generate_password_hash对管理员密码进行哈希处理
- **SQL注入防护**：使用SQLAlchemy ORM，避免直接拼接SQL语句
- **文件上传安全**：验证文件类型和大小，防止恶意文件上传
- **权限控制**：管理员操作需要登录验证

### 5.2 前端安全

- **XSS防护**：对用户输入的文本进行HTML转义
- **文件类型验证**：前端验证文件类型，减少无效请求
- **消息格式化**：安全处理消息中的特殊格式，防止XSS攻击

## 6. 使用指南

### 6.1 系统配置

#### 配置文件
主要配置项位于app.py文件中：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| SECRET_KEY | 会话密钥 | your-secret-key |
| SQLALCHEMY_DATABASE_URI | 数据库连接字符串 | sqlite:///chat.db |
| UPLOAD_FOLDER | 文件上传目录 | uploads |
| MAX_CONTENT_LENGTH | 文件上传大小限制 | 1GB |
| ALLOWED_EXTENSIONS | 允许的文件扩展名 | {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi', 'wmv'} |
| RESET_DATABASE_ON_RESTART | 重启是否重置数据库 | True |

### 6.2 管理员登录

1. 访问 `http://localhost:5000/admin`
2. 输入默认用户名：admin
3. 输入默认密码：admin123
4. 点击登录按钮

### 6.3 消息格式化语法

在设置自动回复、关键词回复、打招呼语句时，可以使用以下格式化语法：

- **加粗文本**：使用 `**文本**` 格式，例如：`**这是加粗文本**`
- **彩色文本**：使用 `#color#文本#` 格式，支持的颜色包括：
  - 基本颜色：red, green, blue, yellow, purple, orange
  - 扩展颜色：black, white, gray, grey, pink, brown, cyan, magenta
  例如：`#red#这是红色文本#`
- **换行**：直接在文本中使用换行符（Enter键）
- **链接**：直接在文本中输入网址，会自动添加点击复制功能

### 6.4 常见操作

#### 添加关键词自动回复
1. 登录管理员后台
2. 点击左侧菜单中的"关键词自动回复"
3. 填写关键词和回复内容
4. 选择消息类型（文本、图片、视频）
5. 点击添加按钮

#### 设置常见问题
1. 登录管理员后台
2. 点击左侧菜单中的"常见问题"
3. 填写问题和答案内容
4. 选择消息类型（文本、图片、视频）
5. 点击添加按钮

#### 设置打招呼语句
1. 登录管理员后台
2. 点击左侧菜单中的"打招呼语句"
3. 填写欢迎消息内容
4. 选择消息类型（文本、图片、视频）
5. 点击添加按钮

## 7. 开发与部署

### 7.1 开发环境搭建

1. **安装依赖**
   ```bash
   pip install flask flask-sqlalchemy werkzeug
   ```

2. **运行项目**
   ```bash
   python app.py
   ```

3. **访问项目**
   - 用户端：http://localhost:5000
   - 管理员端：http://localhost:5000/admin

### 7.2 部署建议

- **生产环境**：建议使用Gunicorn或uWSGI作为WSGI服务器
- **数据库**：生产环境建议使用PostgreSQL或MySQL
- **文件存储**：生产环境建议使用云存储服务
- **HTTPS**：生产环境建议启用HTTPS

## 8. 故障排除

### 8.1 常见问题

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| 无法登录管理员后台 | 用户名或密码错误 | 检查用户名和密码，默认用户名admin，密码admin123 |
| 文件上传失败 | 文件类型不支持或大小超过限制 | 检查文件类型和大小，确保符合系统要求 |
| 消息发送失败 | 网络连接问题或服务器错误 | 检查网络连接，查看服务器日志 |
| 自动回复不生效 | 关键词匹配失败 | 检查关键词设置，确保关键词正确 |

### 8.2 日志查看

Flask应用默认在控制台输出日志信息，生产环境建议配置详细的日志记录。

## 9. 版本历史

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| v1.0 | 2026-01-21 | 初始版本发布 |

## 10. 附录

### 10.1 数据库表结构

#### User表
| 字段名 | 数据类型 | 约束 | 描述 |
|--------|----------|------|------|
| id | Integer | Primary Key | 用户ID |
| user_id | String(50) | Unique, Not Null | 用户唯一标识 |
| alias | String(100) | Default '' | 用户别名 |
| ip_address | String(50) | | IP地址 |
| user_agent | String(255) | | 浏览器信息 |
| remark | Text | Default '' | 用户备注 |
| created_at | DateTime | Default utcnow | 创建时间 |

#### Message表
| 字段名 | 数据类型 | 约束 | 描述 |
|--------|----------|------|------|
| id | Integer | Primary Key | 消息ID |
| user_id | String(50) | ForeignKey, Not Null | 用户ID |
| content | Text | Not Null | 消息内容 |
| is_admin | Boolean | Default False | 是否管理员消息 |
| is_read | Boolean | Default False | 是否已读 |
| message_type | String(20) | Default 'text' | 消息类型 |
| created_at | DateTime | Default utcnow | 创建时间 |

#### Admin表
| 字段名 | 数据类型 | 约束 | 描述 |
|--------|----------|------|------|
| id | Integer | Primary Key | 管理员ID |
| username | String(50) | Unique, Not Null | 用户名 |
| password | String(100) | Not Null | 密码哈希 |

#### AutoReply表
| 字段名 | 数据类型 | 约束 | 描述 |
|--------|----------|------|------|
| id | Integer | Primary Key | 自动回复ID |
| keyword | String(100) | Not Null | 关键词 |
| content | Text | Not Null | 回复内容 |
| message_type | String(20) | Default 'text', Not Null | 消息类型 |
| order_index | Integer | Default 0, Not Null | 排序索引 |

#### CommonQuestion表
| 字段名 | 数据类型 | 约束 | 描述 |
|--------|----------|------|------|
| id | Integer | Primary Key | 常见问题ID |
| question | String(255) | Not Null | 问题 |
| content | Text | Not Null | 答案内容 |
| message_type | String(20) | Default 'text', Not Null | 消息类型 |
| order_index | Integer | Default 0, Not Null | 排序索引 |

#### WelcomeMessage表
| 字段名 | 数据类型 | 约束 | 描述 |
|--------|----------|------|------|
| id | Integer | Primary Key | 打招呼语句ID |
| content | Text | Not Null | 消息内容 |
| message_type | String(20) | Default 'text', Not Null | 消息类型 |
| order_index | Integer | Default 0, Not Null | 排序索引 |

#### SystemSetting表
| 字段名 | 数据类型 | 约束 | 描述 |
|--------|----------|------|------|
| id | Integer | Primary Key | 设置ID |
| key | String(50) | Unique, Not Null | 设置键 |
| value | String(255) | Not Null | 设置值 |

### 10.2 API接口

#### 用户端接口

| 接口 | 方法 | 描述 | 请求参数 | 响应 |
|------|------|------|----------|------|
| / | GET | 首页，获取用户聊天界面 | 无 | HTML页面 |
| /get_messages | POST | 获取用户的所有消息 | user_id: 用户ID | JSON格式的消息列表 |
| /send_message | POST | 发送消息 | user_id: 用户ID, content: 消息内容, message_type: 消息类型 | {"status": "success"} |
| /upload | POST | 上传文件 | file: 文件 | {"status": "success", "filename": "文件名", "message_type": "消息类型"} |

#### 管理员端接口

| 接口 | 方法 | 描述 | 请求参数 | 响应 |
|------|------|------|----------|------|
| /admin | GET | 管理员登录页面 | 无 | HTML页面 |
| /admin/login | POST | 管理员登录 | username: 用户名, password: 密码 | 重定向到管理员控制台 |
| /admin/logout | GET | 管理员登出 | 无 | 重定向到登录页面 |
| /admin/dashboard | GET | 管理员控制台 | 无 | HTML页面 |
| /admin/chat/<user_id> | GET | 与指定用户聊天 | user_id: 用户ID | HTML页面 |
| /admin/send_message | POST | 管理员发送消息 | user_id: 用户ID, content: 消息内容, message_type: 消息类型 | {"status": "success"} |
| /admin/upload | POST | 管理员上传文件 | file: 文件 | {"status": "success", "filename": "文件名", "message_type": "消息类型"} |
| /admin/auto_replies | GET | 关键词自动回复设置页面 | 无 | HTML页面 |
| /admin/add_auto_reply | POST | 添加关键词自动回复 | keyword: 关键词, content: 回复内容, message_type: 消息类型, order_index: 排序索引 | {"status": "success"} |
| /admin/delete_auto_reply/<id> | GET | 删除关键词自动回复 | id: 自动回复ID | 重定向到自动回复设置页面 |
| /admin/common_questions | GET | 常见问题设置页面 | 无 | HTML页面 |
| /admin/add_common_question | POST | 添加常见问题 | question: 问题, content: 答案内容, message_type: 消息类型, order_index: 排序索引 | {"status": "success"} |
| /admin/delete_common_question/<id> | GET | 删除常见问题 | id: 常见问题ID | 重定向到常见问题设置页面 |
| /admin/welcome_messages | GET, POST | 打招呼语句设置页面 | 无 | HTML页面 |
| /admin/delete_welcome_message/<id> | GET | 删除打招呼语句 | id: 打招呼语句ID | 重定向到打招呼语句设置页面 |
| /admin/settings | GET, POST | 系统设置页面 | 无 | HTML页面 |
| /admin/change_password | POST | 修改管理员密码 | current_password: 当前密码, new_password: 新密码, confirm_password: 确认密码 | 重定向到系统设置页面 |
| /admin/delete_user/<user_id> | GET | 删除用户 | user_id: 用户ID | 重定向到管理员控制台 |
| /admin/update_user_info | POST | 更新用户信息 | user_id: 用户ID, alias: 别名, remark: 备注 | {"status": "success"} |

### 10.3 代码优化建议

1. **数据库优化**
   - 生产环境建议使用PostgreSQL或MySQL，提高性能和可靠性
   - 添加适当的索引，提高查询速度

2. **前端优化**
   - 使用WebSocket代替轮询，实现真正的实时通信
   - 优化图片和视频的加载，考虑使用懒加载
   - 使用前端框架（如Vue.js、React）提高开发效率

3. **后端优化**
   - 使用异步处理，提高并发性能
   - 实现消息队列，处理异步任务
   - 添加缓存机制，减少数据库查询

4. **安全优化**
   - 实现CSRF保护
   - 添加请求频率限制，防止暴力攻击
   - 定期备份数据库

5. **可维护性优化**
   - 模块化代码，分离业务逻辑
   - 添加详细的日志记录
   - 编写单元测试

## 11. 总结

在线客服系统是一个功能完整、易于使用的Web应用，为用户和客服人员提供了便捷的实时沟通渠道。系统支持文本、图片、视频等多种消息类型，以及关键词自动回复、常见问题快速选择等功能，大大提高了客服效率和用户体验。

系统采用Flask框架开发，结构清晰，代码简洁，易于维护和扩展。通过实施多种安全措施，确保了系统的安全性和可靠性。

未来，系统可以通过添加更多功能，如多语言支持、消息统计分析、客服满意度评价等，进一步提升系统的实用性和用户体验。