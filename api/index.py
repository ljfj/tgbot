import os
import logging
import json
import importlib
# 我们不再需要在全局作用域使用 asyncio
# import asyncio 

from telegram import Update
from telegram.ext import Application, PicklePersistence, ExtBot
# 我们不再需要自定义 request，因为我们将使用正确的事件循环管理
# from telegram.request import HTTPXRequest 
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

# --- 创建 Application 对象 ---
# ✨ 1. 回归到最标准的 Application 创建方式
# 我们只提供 token 和 persistence。让 Application 自己去创建内部的 ExtBot。
# 这能确保所有内部组件都正确地相互连接。
application = (
    Application.builder()
    .token(TOKEN)
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

# --- Starlette 应用与正确的初始化流程 ---
app = Starlette()

# ✨ 2. 恢复使用 startup 和 shutdown 事件
# 这是处理异步应用生命周期的标准方法
@app.on_event("startup")
async def startup_event():
    """
    在 Starlette 应用启动时，执行初始化。
    """
    # 持久化数据会在 initialize() 中被加载
    await application.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    """
    在 Starlette 应用关闭时，确保持久化数据被保存。
    """
    await application.shutdown()

@app.route("/", methods=["POST"])
async def webhook(request: Request) -> Response:
    """
    这个端点现在只负责处理 Webhook 更新。
    """
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        
        # ✨ 3. process_update 会自动处理持久化数据的加载和保存
        # 我们不需要手动调用任何 update/flush 方法
        await application.process_update(update)
        
        return Response(content="OK", status_code=200)
    except Exception as e:
        logging.error(f"Error processing update: {e}", exc_info=True)
        return Response(content="Internal Server Error", status_code=500)

# ✨ 4. 彻底移除了全局的 asyncio.run() 调用。
