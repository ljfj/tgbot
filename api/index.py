# api/index.py
import os
import logging
import json
import importlib
from http.server import BaseHTTPRequestHandler
import asyncio

from telegram import Update
from telegram.ext import Application, JobQueue
from .kv_persistence import VercelKVPersistence # 导入我们自己的持久化类

logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("TOKEN") # Vercel 会自动注入 KV 相关的环境变量

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        async def main():
            # 使用我们自定义的 VercelKVPersistence
            persistence = VercelKVPersistence()
            
            application = (
                Application.builder()
                .token(TOKEN)
                .persistence(persistence)
                .job_queue(JobQueue()) # 启用 JobQueue
                .build()
            )

            # ... (加载命令的代码保持不变) ...
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

            # ... (处理请求的代码保持不变) ...
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            update = Update.de_json(json.loads(post_data), application.bot)
            
            await application.initialize()
            await application.process_update(update)
            await application.shutdown()

        try:
            asyncio.run(main())
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'Success')
        except Exception as e:
            logging.error(f"Error: {e}", exc_info=True)
            self.send_response(500)
            self.end_headers()

        return
