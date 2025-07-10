# api/index.py
import os
import logging
import json
import importlib
import asyncio

from telegram import Update, Bot
from telegram.ext import Application, ExtBot
from telegram.request import HTTPXRequest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response

# --- 全局配置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable not set!")

# --- 自定义 Request 配置 ---
# 这个对于解决 "Event loop is closed" 问题至关重要
custom_request = HTTPXRequest(http_version="1.1")

# --- 创建 Application 对象 ---
# 使用 ExtBot 以兼容所有扩展功能，并传入自定义 request
bot = ExtBot(token=TOKEN, request=custom_request)
application = Application.builder().bot(bot).build()

# --- 命令插件加载与注册 ---
def load_and_register_commands(app: Application):
    commands_dir = os.path.join(os.path.dirname(__file__), 'commands')
    for filename in os.listdir(commands_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = f"api.commands.{filename[:-3]}"
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, "register"):
                    module.register(app)
                    logging.info(f"Successfully registered handler from: {module_name}")
            except Exception as e:
                logging.error(f"Failed to load module {module_name}: {e}", exc_info=True)

load_and_register_commands(application)

# --- 全局初始化 ---
# 这是在 Vercel 上可靠初始化的关键
try:
    asyncio.run(application.initialize())
    logging.info("Application initialized successfully in global scope.")
except Exception as e:
    logging.error(f"Failed to initialize application in global scope: {e}", exc_info=True)

# --- Starlette 应用 ---
# Vercel 会识别并运行这个名为 'app' 的 ASGI 对象
app = Starlette()

@app.route("/", methods=["POST"])
async def webhook(request: Request) -> Response:
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return Response(content="OK", status_code=200)
    except Exception as e:
        logging.error(f"Error processing update: {e}", exc_info=True)
        return Response(content="Internal Server Error", status_code=500)
