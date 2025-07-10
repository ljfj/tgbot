import os
import logging
import json
import importlib
# 我们不再需要在全局作用域使用 asyncio
# import asyncio 

from telegram import Update
from telegram.ext import Application, PicklePersistence
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response

# --- 全局配置 ---
logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable not set!")

# --- 持久化配置 ---
# 这部分保持不变
persistence = PicklePersistence(filepath="/tmp/conversation_persistence")

# --- 创建 Application 对象 ---
# 这部分也保持不变，持久化已经启用
application = (
    Application.builder()
    .token(TOKEN)
    .persistence(persistence)
    .build()
)

# --- 命令插件加载与注册 ---
# 这部分也保持不变
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

# --- Starlette 应用与正确的初始化流程 ---
app = Starlette()

@app.on_event("startup")
async def startup_event():
    """
    在 Starlette 应用启动时，执行初始化。
    Vercel 在处理第一个请求前会触发这个事件。
    """
    try:
        # 在 Starlette 自己的事件循环中初始化机器人
        await application.initialize()
        logging.info("Application initialized successfully within Starlette startup event.")
    except Exception as e:
        logging.error(f"Failed to initialize application in startup_event: {e}", exc_info=True)

# 我们不需要 shutdown 事件，因为 Vercel 的函数是短暂的
# @app.on_event("shutdown")
# async def shutdown_event():
#     await application.shutdown()

@app.route("/", methods=["POST"])
async def webhook(request: Request) -> Response:
    """
    这个端点现在只负责处理 Webhook 更新。
    初始化的工作已经交给了 startup 事件。
    """
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        # 持久化现在是自动处理的，我们不需要手动调用任何相关方法
        await application.process_update(update)
        return Response(content="OK", status_code=200)
    except Exception as e:
        logging.error(f"Error processing update: {e}", exc_info=True)
        return Response(content="Internal Server Error", status_code=500)

# ✨ 移除了全局的 asyncio.run() 调用。这是最关键的改动。
