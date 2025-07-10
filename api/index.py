import os
import logging
import json
import importlib
import asyncio

from telegram import Update
from telegram.ext import Application

# --- 全局配置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable not set!")

# --- Vercel 的主入口函数 ---
# 这是 Vercel 真正调用的函数
# 我们不再使用 Starlette，而是直接使用 Vercel 的标准 Python handler
async def handler(event, context):
    """
    Vercel Serverless Function entry point.
    为每个请求创建一个全新的、独立的 Application 实例。
    """
    
    # 1. 在函数内部创建 Application 对象
    # 这是最核心的改动，确保每次请求都有一个全新的实例。
    # 我们使用最简单的 builder，不添加任何可能引起冲突的自定义项。
    application = Application.builder().token(TOKEN).build()

    # 2. 在函数内部加载所有命令
    # 这确保了所有 handler 都被注册到了这个全新的 application 实例上。
    commands_dir = os.path.join(os.path.dirname(__file__), 'commands')
    for filename in os.listdir(commands_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = f"api.commands.{filename[:-3]}"
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, "register"):
                    # 将 handler 注册到我们刚刚创建的这个 application 实例上
                    module.register(application)
            except Exception as e:
                logging.error(f"Failed to load or register module {module_name}: {e}", exc_info=True)

    try:
        # 3. 解析请求体并处理更新
        # 整个过程 (initialize, process_update, shutdown) 都在同一个事件循环中完成。
        body = json.loads(event.get("body", "{}"))
        update = Update.de_json(body, application.bot)
        
        await application.initialize()
        await application.process_update(update)
        await application.shutdown()
        
        # 4. 返回成功响应
        return {'statusCode': 200, 'body': 'Success'}
        
    except Exception as e:
        logging.error(f"Error in handler: {e}", exc_info=True)
        return {'statusCode': 500, 'body': 'Internal Server Error'}
