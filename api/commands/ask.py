# api/commands/ask.py
import logging
import httpx
from config import API_URL, API_KEY, MODEL_ID

from telegram import Update
# ✨ 1. 不再需要 ConversationHandler 相关的 imports
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# 日志记录
logger = logging.getLogger(__name__)

# ✨ 2. 这是一个简单的、一次性的问答函数
async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /ask 命令，进行一次性问答。"""
    if not update.message:
        return
        
    if context.args:
        user_prompt = " ".join(context.args)
    else:
        await update.message.reply_text("请在 /ask 后面输入你的问题。")
        return

    thinking_message = await update.message.reply_text("🤔 Thinking...")
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # SYSTEM_PROMPT 仍然可以保留，为单次问答提供上下文
    system_prompt = "你是一个乐于助人、知识渊博的AI助手。"
    
    data = {
        "model": MODEL_ID,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(API_URL, headers=headers, json=data)
            response.raise_for_status()
            
            result = response.json()
            ai_reply = result.get("choices", [{}])[0].get("message", {}).get("content", "AI 未能提供有效回复。")
            
            await context.bot.edit_message_text(
                text=ai_reply,
                chat_id=thinking_message.chat_id,
                message_id=thinking_message.message_id
            )

    except Exception as e:
        logger.error(f"Error in ask_command: {e}", exc_info=True)
        await context.bot.edit_message_text(
            text=f"请求 AI 时出错: {e}",
            chat_id=thinking_message.chat_id,
            message_id=thinking_message.message_id
        )

# ✨ 3. 注册器现在只注册一个简单的 CommandHandler
def register(app: Application):
    """将 /ask 命令处理器注册到 application"""
    app.add_handler(CommandHandler("ask", ask_command))
