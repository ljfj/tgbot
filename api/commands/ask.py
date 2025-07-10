# api/commands/ask.py (使用这个最简单的版本)
import logging
import httpx
from config import API_URL, API_KEY, MODEL_ID
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logger = logging.getLogger(__name__)

async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not context.args:
        await update.message.reply_text("请在 /ask 后面输入你的问题。")
        return
    
    user_prompt = " ".join(context.args)
    thinking_message = await update.message.reply_text("🤔 Thinking...")
    
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    data = {"model": MODEL_ID, "messages": [{"role": "user", "content": user_prompt}]}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(API_URL, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            ai_reply = result.get("choices", [{}])[0].get("message", {}).get("content", "AI 未能提供有效回复。")
            await context.bot.edit_message_text(text=ai_reply, chat_id=thinking_message.chat_id, message_id=thinking_message.message_id)
    except Exception as e:
        logger.error(f"Error in ask_command: {e}", exc_info=True)
        await context.bot.edit_message_text(text=f"请求 AI 时出错: {e}", chat_id=thinking_message.chat_id, message_id=thinking_message.message_id)

def register(app: Application):
    app.add_handler(CommandHandler("ask", ask_command))
