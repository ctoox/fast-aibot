from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.bot import WeixinBot
from app.models import IncomingMessage
import logging
import uvicorn

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Weixin Bot Echo Example")

bot = WeixinBot()


@bot.on_message
async def echo_handler(msg: IncomingMessage):
    logger.info(f"[{msg.timestamp.strftime('%X')}] {msg.user_id}: {msg.text}")
    await bot.send_typing(msg.user_id)
    await bot.reply(msg, f"你说了: {msg.text}")


@app.get("/")
async def root():
    return {"status": "running", "bot_user": bot._credentials.user_id if bot._credentials else "not logged in"}


@app.post("/webhook")
async def webhook(msg: dict):
    """接收微信消息的webhook端点"""
    from app.models import WeixinMessage
    try:
        message = WeixinMessage(**msg)
        incoming = bot._to_incoming_message(message)
        if incoming:
            await bot._dispatch_message(incoming)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"status": "error", "detail": str(e)}


if __name__ == "__main__":
    # 先登录
    bot.login()
    logger.info(f"Bot logged in as {bot._credentials.user_id}")
    
    # 启动FastAPI服务
    uvicorn.run(app, host="0.0.0.0", port=8000)
