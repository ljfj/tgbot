import os
import logging
import json
import importlib
import asyncio

from telegram import Update
# ✨ 1. 导入 Bot, HTTPXRequest
from telegram.ext import Application, PicklePersistence, Bot
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

# ✨ 2. 创建一个自定义的 Request 对象
# 这个 Request 对象在每次需要时都会创建一个新的 httpx.AsyncClient。
# 这可以完美避免 "Event loop is closed" 的问题，因为每个请求都有自己独立的生命周期。
# 在无服务器环境中，这是一个非常健壮的模式。
custom_request = HTTPXRequest(http_version="1.1")


# --- 创建 Application 对象 ---
# ✨ 3. 在 builder 中使用 .bot() 来传入我们自定义的 Bot
# 我们创建一个包含自定义 request 的 Bot 实例
custom_bot = Bot(token=TOKEN, request=custom_request)

application = (
    Application.builder()
    .bot(custom_bot) # <-- 使用我们自定义的 Bot
    .persistence(persistence)
    .build()
)

# --- 命令插件加载与注册 ---
# 这部分保持不变
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

# --- ✨ 4. 恢复使用全局的 asyncio.run() 来强制初始化 ---
# 这是确保应用在处理任何请求前都已初始化的最可靠方法。
try:
    asyncio.run(application.initialize())
    logging.info("Application initialized successfully in global scope.")
except Exception as e:
    logging.error(f"Failed to initialize application in global scope: {e}", exc_info=True)


# --- Starlette 应用 ---
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
