import os
import logging
import json
import importlib

from telegram import Update
# ✨ 1. 回归到最简单的 imports
from telegram.ext import Application
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response

# --- 全局配置 ---
logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable not set!")

# --- 创建 Application 对象 ---
# ✨ 2. 移除所有持久化配置，回归最简单的 builder
application = Application.builder().token(TOKEN).build()

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

# --- Starlette 应用 ---
app = Starlette()

# ✨ 3. 我们不再需要复杂的生命周期事件
# @app.on_event("startup")
# async def startup_event():
#     ...

@app.route("/", methods=["POST"])
async def webhook(request: Request) -> Response:
    """处理 Webhook 更新。"""
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        # ✨ 4. 在处理前，手动初始化。
        # 对于无状态应用，这是一个简单可靠的模式。
        await application.initialize()
        await application.process_update(update)
        return Response(content="OK", status_code=200)
    except Exception as e:
        logging.error(f"Error processing update: {e}", exc_info=True)
        return Response(content="Internal Server Error", status_code=500)
