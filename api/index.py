import os
import logging
import json
import importlib
import asyncio

from telegram import Update
from telegram.ext import Application, ExtBot
from telegram.request import HTTPXRequest

# --- 全局配置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable not set!")

# --- 创建 Application 的工厂函数 ---
# 我们不再在全局创建 application，而是在每次调用 handler 时创建
# 这能确保每个请求都有一个全新的、干净的应用实例和事件循环
def create_application() -> Application:
    """Creates and configures a new PTB Application instance."""
    
    # 自定义 Request 对象，以避免潜在的连接池问题
    custom_request = HTTPXRequest(http_version="1.1")
    bot = ExtBot(token=TOKEN, request=custom_request)
    
    application = Application.builder().bot(bot).build()

    # --- 命令插件加载与注册 ---
    commands_dir = os.path.join(os.path.dirname(__file__), 'commands')
    for filename in os.listdir(commands_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = f"api.commands.{filename[:-3]}"
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, "register"):
                    module.register(application)
            except Exception as e:
                # 在 Vercel 日志中打印更详细的加载错误
                logging.error(f"Failed to load or register module {module_name}: {e}", exc_info=True)
                
    return application

# --- Vercel 的主入口函数 ---
# 这就是 Vercel 会调用的唯一函数
async def handler(event, context):
    """Vercel Serverless Function entry point."""
    
    # 1. 为每个请求创建一个全新的 Application 实例
    application = create_application()
    
    # 2. 初始化这个实例
    await application.initialize()
    
    try:
        # 3. 解析请求并处理
        body = json.loads(event.get("body", "{}"))
        update = Update.de_json(body, application.bot)
        
        await application.process_update(update)
        
        # 4. 在函数结束前，优雅地关闭
        await application.shutdown()
        
        return {'statusCode': 200, 'body': 'Success'}
        
    except Exception as e:
        logging.error(f"Error in handler: {e}", exc_info=True)
        return {'statusCode': 500, 'body': 'Internal Server Error'}
