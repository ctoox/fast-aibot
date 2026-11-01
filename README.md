# Weixin Bot FastAPI 版本

基于 FastAPI 重构的微信 iLink Bot SDK，提供 RESTful API 接口。

## 项目结构

```
fast_aibot/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI 主应用
│   ├── bot.py          # 机器人核心逻辑
│   ├── api_client.py   # 微信 API 客户端
│   ├── auth.py         # 认证和登录
│   ├── models.py       # Pydantic 数据模型
│   └── config.py      # 配置管理
├── examples/
│   └── echo_bot.py    # 示例：回声机器人
├── tests/
├── requirements.txt
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
cd fast_aibot
pip install -r requirements.txt
```

### 2. 登录

设置环境变量或使用默认配置：

```bash
export WEIXIN_BOT_BASE_URL="https://ilinkai.weixin.qq.com"
export WEIXIN_BOT_TOKEN_PATH="~/.weixin-bot/credentials.json"
```

运行登录（扫码登录微信）：

```bash
python -c "from app.auth import login; login(force=True)"
```

### 3. 启动服务

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

或使用示例：

```bash
python examples/echo_bot.py
```

## API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/` | GET | 服务状态 |
| `/login` | POST | 登录（强制重新登录） |
| `/credentials` | GET | 获取当前凭证 |
| `/credentials` | DELETE | 清除凭证 |
| `/send` | POST | 发送消息 |
| `/reply` | POST | 回复消息 |
| `/webhook` | POST | 接收微信消息的 webhook |
| `/register-handler` | POST | 注册消息处理器 |

## 配置项

通过环境变量 `WEIXIN_BOT_` 前缀配置：

- `WEIXIN_BOT_BASE_URL`: API 基础 URL（默认：https://ilinkai.weixin.qq.com）
- `WEIXIN_BOT_TOKEN_PATH`: 凭证存储路径（默认：~/.weixin-bot/credentials.json）
- `WEIXIN_BOT_HOST`: 服务监听地址（默认：0.0.0.0）
- `WEIXIN_BOT_PORT`: 服务端口（默认：8000）
- `WEIXIN_BOT_DEBUG`: 调试模式（默认：False）
- `WEIXIN_BOT_WEBHOOK_URL`: Webhook URL（可选）

## 使用示例

### 作为 Python 库使用

```python
from app.bot import WeixinBot
import asyncio

bot = WeixinBot()
bot.login()

@bot.on_message
async def handle(msg):
    print(f"{msg.user_id}: {msg.text}")
    await bot.reply(msg, f"你说了: {msg.text}")

# 运行轮询
asyncio.run(bot.get_updates_once())
```

### 作为 HTTP 服务使用

```bash
# 启动服务
uvicorn app.main:app --reload

# 发送消息
curl -X POST "http://localhost:8000/send?user_id=USER_ID&text=Hello"

# 注册处理器
curl -X POST "http://localhost:8000/register-handler?handler_type=echo"
```

## 与原版区别

| 特性 | 原版 (weixin_bot) | FastAPI 版 |
|------|-------------------|------------|
| 框架 | asyncio + SDK | FastAPI + SDK |
| 接口 | Python API | RESTful API + Python API |
| 数据模型 | TypedDict + dataclass | Pydantic v2 |
| 配置 | 参数传入 | pydantic-settings |
| 部署 | 脚本运行 | HTTP 服务 |

## 开发

```bash
# 安装开发依赖
pip install -r requirements.txt

# 运行测试
pytest tests/

# 代码检查
ruff check app/
```

## License

与原始项目保持一致。
