from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .models import Credentials, IncomingMessage, WeixinMessage
from .bot import WeixinBot
from .auth import login, load_credentials, clear_credentials

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

bot_instance: WeixinBot | None = None
polling_task: asyncio.Task[Any] | None = None

# 聊天会话存储
chat_sessions: Dict[str, Dict[str, Any]] = {}
# 当前活跃用户ID（从微信登录获取）
current_user_id: str = ""
model_providers = {
    "longcat": {
        "api_key": "",  # 需要配置
        "base_url": "https://api.longcat.ai",
        "model": "longcat-chat",
        "max_tokens": 4096
    },
    "mock": {
        "api_key": "mock-key",
        "base_url": "",  # 不使用真实API
        "model": "mock-model",
        "max_tokens": 4096
    },
    # 其他模型配置...
}


def _get_bot() -> WeixinBot:
    global bot_instance
    if bot_instance is None:
        bot_instance = WeixinBot()
    return bot_instance


async def _poll_loop(bot: WeixinBot) -> None:
    global current_user_id
    while True:
        try:
            messages = await bot.get_updates_once()
            for msg in messages:
                # 自动更新当前用户ID（如果收到消息）
                if msg.user_id and not current_user_id:
                    current_user_id = msg.user_id
                    logger.info(f"检测到用户ID: {current_user_id}")
                await bot._dispatch_message(msg)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Poll error: {e}")
            await asyncio.sleep(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global polling_task, current_user_id
    settings = get_settings()
    bot = _get_bot()

    await bot._ensure_credentials()
    current_user_id = bot._credentials.user_id if bot._credentials else ""
    logger.info(f"Bot logged in as {current_user_id}")

    polling_task = asyncio.create_task(_poll_loop(bot))
    yield
    if polling_task:
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Weixin Bot FastAPI",
    description="FastAPI wrapper for WeChat iLink Bot",
    version="1.0.0",
    lifespan=lifespan,
)

# 添加静态文件服务
app.mount("/static", StaticFiles(directory="examples"), name="static")


@app.get("/", response_class=HTMLResponse)
async def get_chat_page():
    return FileResponse("examples/chat.html")


@app.get("/api/status")
async def get_status():
    bot = _get_bot()
    return {
        "status": "running",
        "bot_user": bot._credentials.user_id if bot._credentials else "not logged in",
        "current_user_id": current_user_id,
        "active_sessions": len(chat_sessions)
    }


@app.post("/login")
async def login_bot(force: bool = False):
    try:
        credentials = await login(force=force)
        return {"status": "success", "user_id": credentials.user_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/credentials")
async def get_credentials():
    cred = await load_credentials()
    if cred is None:
        raise HTTPException(status_code=404, detail="No credentials found")
    return cred.model_dump()


@app.delete("/credentials")
async def delete_credentials():
    await clear_credentials()
    return {"status": "cleared"}


@app.post("/send")
async def send_message(user_id: str, text: str):
    bot = _get_bot()
    try:
        await bot.send(user_id, text)
        return {"status": "sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reply")
async def reply_message(user_id: str, context_token: str, text: str):
    bot = _get_bot()
    try:
        msg = IncomingMessage(
            user_id=user_id,
            text="",
            type="text",
            raw=WeixinMessage(
                message_id=0,
                from_user_id=user_id,
                to_user_id="",
                client_id="",
                create_time_ms=0,
                message_type=1,
                message_state=2,
                context_token=context_token,
                item_list=[],
            ),
            timestamp=datetime.now(),
        )
        await bot.reply(msg, text)
        return {"status": "replied"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhook")
async def receive_webhook(message: WeixinMessage, background_tasks: BackgroundTasks):
    bot = _get_bot()
    incoming = bot._to_incoming_message(message)
    if incoming is None:
        return {"status": "ignored"}

    # 更新当前用户ID
    global current_user_id
    if incoming.user_id and not current_user_id:
        current_user_id = incoming.user_id
        logger.info(f"Webhook检测到用户ID: {current_user_id}")

    background_tasks.add_task(bot._dispatch_message, incoming)
    return {"status": "accepted"}


@app.post("/register-handler")
async def register_handler_endpoint(handler_type: str = "echo"):
    bot = _get_bot()

    if handler_type == "echo":
        async def echo_handler(msg: IncomingMessage):
            logger.info(f"[Echo] {msg.user_id}: {msg.text}")
            await bot.reply(msg, f"Echo: {msg.text}")
        bot.on_message(echo_handler)
    elif handler_type == "log":
        async def log_handler(msg: IncomingMessage):
            logger.info(f"[Log] {msg.timestamp} {msg.user_id}: {msg.text}")
        bot.on_message(log_handler)
    else:
        raise HTTPException(status_code=400, detail="Unknown handler type")

    return {"status": "handler registered", "type": handler_type}


# ==================== 聊天API ====================

@app.post("/chat/completions")
async def chat_completions(request: Request):
    global current_user_id
    try:
        data = await request.json()
        message = data.get("message", "")
        user_id = data.get("user_id", current_user_id)  # 使用当前用户ID作为默认
        model = data.get("model", "longcat")
        temperature = data.get("temperature", 0.7)
        max_tokens = data.get("max_tokens", 2048)
        api_key = data.get("api_key", "")  # 从请求中获取API密钥

        if not message:
            return {"success": False, "message": "消息内容不能为空"}

        if not user_id:
            return {"success": False, "message": "用户ID未知，请先发送一条消息到微信"}

        # 获取模型配置
        model_config = model_providers.get(model)
        if not model_config:
            return {"success": False, "message": f"模型 {model} 未配置"}

        # 如果选择mock模型，直接返回模拟响应
        if model == "mock":
            return {
                "id": f"mock-{datetime.now().timestamp()}",
                "choices": [
                    {
                        "text": f"这是模拟响应：你说了 '{message}'",
                        "index": 0
                    }
                ],
                "usage": {
                    "total_tokens": len(message) + 20,
                    "prompt_tokens": len(message),
                    "completion_tokens": 20
                }
            }

        # 检查API密钥
        if not api_key and not model_config.get("api_key"):
            return {
                "success": False, 
                "message": f"模型 {model} 需要API密钥，请在聊天页面的AI配置中设置"
            }

        # 调用真实API
        import aiohttp
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {api_key or model_config['api_key']}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model_config["model"],
                "messages": [
                    {"role": "user", "content": message}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            async with session.post(
                f"{model_config['base_url']}/v1/chat/completions",
                headers=headers,
                json=payload
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    return {"success": False, "message": f"API调用失败: {error_text}"}
                    
                result = await resp.json()
                
                # 更新token计数
                session_id = f"session_{user_id}"
                if session_id in chat_sessions:
                    chat_sessions[session_id]["token_count"] += result.get("usage", {}).get("total_tokens", 0)
                
                return result

    except Exception as e:
        logger.error(f"Chat completion error: {e}")
        return {"success": False, "message": str(e)}


@app.get("/api/conversations")
async def get_conversations():
    # 返回所有会话的元数据
    sessions_meta = {}
    for session_id, session_data in chat_sessions.items():
        sessions_meta[session_id] = {
            "id": session_id,
            "title": session_data.get("title", "Untitled"),
            "created_at": session_data.get("created_at", ""),
            "token_count": session_data.get("token_count", 0),
            "last_message": session_data.get("last_message", "")
        }
    return {"conversations": sessions_meta}


@app.post("/api/conversations")
async def create_conversation():
    global current_user_id
    session_id = f"conv_{datetime.now().timestamp()}"
    chat_sessions[session_id] = {
        "id": session_id,
        "title": f"对话 {len(chat_sessions) + 1}",
        "messages": [],
        "created_at": datetime.now().isoformat(),
        "token_count": 0,
        "last_message": "",
        "user_id": current_user_id
    }
    return {"session_id": session_id}


@app.delete("/api/conversations/{session_id}")
async def delete_conversation(session_id: str):
    if session_id in chat_sessions:
        del chat_sessions[session_id]
        return {"success": True}
    return {"success": False, "message": "会话不存在"}


@app.get("/api/models")
async def get_models():
    return {
        "models": [
            {"id": "mock", "name": "模拟模式", "provider": "本地"},
            {"id": "longcat", "name": "LongCat Chat", "provider": "LongCat"},
            {"id": "groq", "name": "Groq Llama", "provider": "Groq"},
            {"id": "gemini", "name": "Google Gemini", "provider": "Google"},
            {"id": "claude", "name": "Anthropic Claude", "provider": "Anthropic"},
            {"id": "gpt4", "name": "OpenAI GPT-4", "provider": "OpenAI"}
        ]
    }


@app.post("/api/config")
async def save_config(request: Request):
    try:
        config = await request.json()
        # 保存模型配置
        for model_id, model_config in config.items():
            if model_id in model_providers:
                model_providers[model_id].update(model_config)
        return {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.get("/api/config")
async def get_config():
    return model_providers


@app.get("/api/user-id")
async def get_current_user_id():
    global current_user_id
    return {
        "user_id": current_user_id,
        "is_logged_in": bool(current_user_id)
    }


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(app, host=settings.host, port=settings.port)