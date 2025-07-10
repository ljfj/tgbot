import os
import logging
import json
import importlib
import asyncio

from telegram import Update, Bot
from telegram.ext import Application, ExtBot
# 我们不再需要持久化，因为我们已经确认它在 Vercel 上不可靠
# from telegram.ext import PicklePersistence 
from telegram.request import HTTPXRequest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response

# --- 全局配置 ---
logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable not set!")

# --- 自定义 Request 配置 ---
# 这个对于解决 "Event loop is closed" 至关重要
custom_request = HTTPXRequest(http_version="1.1")

# --- 创建 Application 对象 ---
# ✨ 1. 使用 ExtBot 来创建 Bot 实例，以兼容所有扩展功能
# 注意：我们在这里不使用 Application.builder()，而是手动构建，以获得最大控制权
# ExtBot 可以直接使用，不需要 builder
bot = ExtBot(token=TOKEN, request=custom_request)
application = Application.builder().bot(bot).build()


# --- 命令插件加载与注册 ---
# (这部分保持不变)
def load_and_register_commands(app: Application):
    logger = logging.getLogger(__name__)
    logger.info("Starting to load and register commands...")
    commands_dir = os.path.join(os.path.dirname(__file__), 'commands')
    for filename in os.listdir(commands_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = f"api.commands.{filename[:-3]}"
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, "register"):
                    module.register(app)
                    logger.info(f"Successfully registered handlers from: {module_name}")
            except Exception as e:
                logger.error(f"Failed to load module {module_name}: {e}")

load_and_register_commands(application)

# --- 全局初始化 ---
# ✨ 2. 恢复使用全局 asyncio.run()，这是唯一可靠的初始化方式
try:
    asyncio.run(application.initialize())
    logging.info("Application initialized successfully in global scope.")
except Exception as e:
    logging.error(f"Failed to initialize application in global scope: {e}", exc_info=True)

# --- Starlette 应用 ---
app = Starlette()

@app.route("/", methods=["POST"])
async def webhook(request: Request) -> Response:
    """Webhook现在非常纯粹，只负责处理更新。"""
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return Response(content="OK", status_code=200)
    except Exception as e:
        logging.error(f"Error processing update: {e}", exc_info=True)
        return Response(content="Internal Server Error", status_code=500)
