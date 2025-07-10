import os
import logging
import json
import importlib
import asyncio

from telegram import Update
# ✨ 1. 从 telegram.ext 导入 ExtBot，不再使用 telegram.Bot
from telegram.ext import Application, PicklePersistence, ExtBot
from telegram.request import HTTPXRequest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response

# --- 全局配置 ---
logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable not set!")

# --- 持久化配置 ---
persistence = PicklePersistence(filepath="/tmp/conversation_persistence")

# --- 自定义 Request 配置 ---
# 这部分对于解决 event loop 问题仍然是至关重要的
custom_request = HTTPXRequest(http_version="1.1")

# --- 创建 Application 对象 ---
# ✨ 2. 使用 ExtBot 来创建我们的自定义 Bot 实例
# ExtBot 是 Bot 的子类，它包含了持久化等扩展功能所需的全部逻辑。
custom_ext_bot = ExtBot(token=TOKEN, request=custom_request)

application = (
    Application.builder()
    .bot(custom_ext_bot) # <-- 使用我们自定义的 ExtBot 实例
    .persistence(persistence)
    .build()
)

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
# (这部分保持不变)
try:
    asyncio.run(application.initialize())
    logging.info("Application initialized successfully in global scope.")
except Exception as e:
    logging.error(f"Failed to initialize application in global scope: {e}", exc_info=True)


# --- Starlette 应用 ---
# (这部分保持不变)
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
