# NovelGenerator — AI 网文生成器

AI 驱动的长篇网络小说自动生成系统。支持大纲生成、章节续写、知识库一致性维护和批量生成。

## 功能特性

- **AI 大纲生成** — 根据题材和设定自动生成章节大纲
- **章节生成** — SSE 实时流式输出，支持开篇、批量、单章重写
- **知识库系统** — 自动提取人物/地点/事件，跨章节维护一致性
- **多 AI 服务商** — 支持 OpenAI / DeepSeek / 自定义 API，优先级 + 容错切换
- **导出** — 全书 TXT 导出
- **安全** — JWT 认证、密码哈希、API Key 加密存储

## 技术栈

| 层       | 技术                                              |
|---------|--------------------------------------------------|
| 后端     | Python 3.13 · FastAPI · SQLAlchemy (async) · SQLite |
| 前端     | React 19 · TypeScript · Vite · TailwindCSS v4 · Zustand |
| 部署     | Docker Compose · Nginx                            |

## 快速开始

### 前置条件

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose（部署用）

### 本地开发

```bash
# 1. 克隆
git clone https://github.com/zhanglixiong424/NovelGenerator.git
cd NovelGenerator

# 2. 后端
cd backend
pip install -r requirements.txt
python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# 3. 前端（新终端）
cd frontend
npm install
npm run dev
```

#4.关闭之前运行的端口
 lsof -i :8000
 kill -9 8150

首次访问会进入管理员注册页面，创建账户后即可使用。

### Docker 部署

```bash
# 1. 构建前端
cd frontend && npm install && npm run build && cd ..

# 2. 配置环境变量
cat > .env << 'EOF'
JWT_SECRET=你的随机密钥_至少32字符
ENCRYPTION_KEY=你的Fernet密钥
EOF

# 3. 启动
docker compose up -d

# 访问 http://localhost
```

**生成 Fernet 密钥：**
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## 项目结构

```
NovelGenerator/
├── backend/
│   ├── main.py                 # FastAPI 入口
│   ├── app/
│   │   ├── config.py           # 配置（环境变量）
│   │   ├── models.py           # SQLAlchemy 模型
│   │   ├── schemas.py          # Pydantic 请求/响应模型
│   │   ├── database.py         # 数据库连接
│   │   ├── auth.py             # JWT 认证
│   │   ├── encryption.py       # API Key Fernet 加密
│   │   ├── ai_service.py       # AI 服务调用（多服务商容错）
│   │   ├── prompts.py          # 提示词模板
│   │   ├── generation.py       # 生成业务逻辑
│   │   └── routers/
│   │       ├── auth.py         # 认证路由
│   │       ├── ai_config.py    # AI 配置管理路由
│   │       ├── projects.py     # 项目 & 章节 CRUD
│   │       ├── generate.py     # SSE 生成 & 导出
│   │       └── knowledge.py    # 知识库路由
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx             # 应用入口 & 路由
│   │   ├── lib/api.ts          # API 客户端
│   │   ├── stores/             # Zustand 状态管理
│   │   ├── pages/              # 页面组件
│   │   └── components/ui/      # 基础 UI 组件
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml
├── nginx.conf
└── .gitignore
```

## API 文档

启动后端后访问：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 使用流程

1. **注册** → 首次访问创建管理员账户
2. **配置 AI** → 设置 → 添加 AI 服务商（OpenAI / DeepSeek 等）
3. **创建项目** → 填写书名、题材、平台、目标字数
4. **生成大纲** → AI 生成章节大纲 → 审阅修改 → 确认
5. **生成章节** → 开篇生成 → 批量续写 → 逐章审阅
6. **知识维护** → 自动提取人物/地点 → 审阅变更 → 确认
7. **导出** → 全书 TXT 导出

## 测试

```bash
cd backend

# API 单元测试（26 个用例）
python3 test_api.py

# 集成测试（17 个用例）
python3 test_integration.py
```

> 测试前需启动后端服务，使用干净数据库。

## 环境变量

| 变量              | 说明                          | 默认值                  |
|------------------|-------------------------------|------------------------|
| `DATABASE_URL`   | 数据库连接字符串                | `sqlite+aiosqlite:///./data/novel.db` |
| `JWT_SECRET`     | JWT 签名密钥（生产环境必设）     | 不安全默认值             |
| `ENCRYPTION_KEY` | Fernet 加密密钥（用于 API Key）  | 自动生成（重启后失效）    |

## License

MIT
