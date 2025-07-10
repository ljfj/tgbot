import os
import logging
import json
import importlib
import asyncio
from http.server import BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application

# --- 全局配置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
TOKEN = os.getenv("TELEGRAM_TOKEN")

# --- 这是 Vercel 会识别并运行的类 ---
class handler(BaseHTTPRequestHandler):

    # 只处理 POST 请求，因为 Telegram Webhook 使用 POST
    def do_POST(self):
        
        # 1. 读取请求体
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        # 2. 将异步逻辑封装在一个函数中
        async def main():
            # a. 创建一个全新的 Application 实例
            application = Application.builder().token(TOKEN).build()

            # b. 加载所有命令到这个新实例上
            commands_dir = os.path.join(os.path.dirname(__file__), 'commands')
            for filename in os.listdir(commands_dir):
                if filename.endswith(".py") and filename != "__init__.py":
                    module_name = f"api.commands.{filename[:-3]}"
                    try:
                        module = importlib.import_module(module_name)
                        if hasattr(module, "register"):
                            module.register(application)
                    except Exception as e:
                        logging.error(f"Failed to load module {module_name}: {e}", exc_info=True)

            # c. 解析更新并处理
            update = Update.de_json(json.loads(post_data), application.bot)
            await application.initialize()
            await application.process_update(update)
            await application.shutdown()

        try:
            # 3. 在同步的 do_POST 方法中，安全地运行我们的异步逻辑
            # asyncio.run() 会创建、运行并关闭一个全新的事件循环，完美隔离
            asyncio.run(main())
            
            # 4. 向 Telegram 返回 200 OK
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Success')
            
        except Exception as e:
            logging.error(f"Error processing request: {e}", exc_info=True)
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b'Internal Server Error')
            
        return
