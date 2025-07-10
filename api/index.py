import os
import logging
import json
import importlib
import asyncio

from telegram import Update
# ✨ 1. 从 telegram.ext 导入 PicklePersistence
from telegram.ext import Application, PicklePersistence
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response

# --- 全局配置 ---
logging.basicConfig(level=logging.INFO)
# 注意：我们这里不需要从 config 导入 TELEGRAM_TOKEN，因为 Application.builder() 会直接使用它
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable not set!")

# ✨ 2. 创建一个持久化对象
# 我们将数据保存在 Vercel 唯一可写的 /tmp 目录下
persistence = PicklePersistence(filepath="/tmp/conversation_persistence")

# --- 创建 Application 对象 ---
# ✨ 3. 在 builder 中添加 .persistence()
application = (
    Application.builder()
    .token(TOKEN)
    .persistence(persistence) # <-- 添加这一行来启用持久化
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

# --- 在全局作用域强制运行异步初始化 ---
# 这部分保持不变
try:
    asyncio.run(application.initialize())
    logging.info("Application initialized successfully in global scope.")
except Exception as e:
    logging.error(f"Failed to initialize application in global scope: {e}", exc_info=True)


# --- Starlette 应用 ---
# 这部分保持不变
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
