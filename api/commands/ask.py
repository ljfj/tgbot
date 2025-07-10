# api/commands/ask.py
import logging
import httpx
from config import API_URL, API_KEY, MODEL_ID

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

# 日志记录
logger = logging.getLogger(__name__)

# 你可以在这里定义你的系统提示，或者也从 config.py 导入
SYSTEM_PROMPT = """
你是一个名为“智多星”的AI助手。
你的任务是友好、幽默地回答用户的问题。
请始终记住我们之前的对话内容。
"""

# 定义对话状态
ASKING = 1

# --- 对话的入口 ---
async def ask_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """当用户发送 /ask 时，开始一段新的对话。"""
    
    # 创建包含系统提示的初始对话历史
    initial_history = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # 将这个初始历史存入 user_data (现在它会被 Vercel KV 持久化)
    context.user_data['conversation_history'] = initial_history
    
    await update.message.reply_text(
        "你好！你已经开始了一段新的对话。请直接输入你的问题。\n"
        "使用 /end 命令可以随时结束本次对话。\n"
        "如果10分钟没有操作，对话将自动结束。"
    )
    # 进入 ASKING 状态
    return ASKING

# --- 对话进行中 ---
async def ask_continue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """处理用户在对话中发送的消息。"""
    user_prompt = update.message.text
    if not user_prompt:
        return ASKING # 如果是空消息，则保持在当前状态

    # 发送“思考中”消息
    thinking_message = await update.message.reply_text("🤔 Thinking...")
    
    # 从 user_data 获取对话历史 (现在它来自 Vercel KV)
    conversation_history = context.user_data.get('conversation_history', [])
    
    # 如果历史为空（可能发生错误），则重新开始
    if not conversation_history:
        conversation_history = [{"role": "system", "content": SYSTEM_PROMPT}]

    # 将用户的新消息加入历史记录
    conversation_history.append({"role": "user", "content": user_prompt})
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 发送包含完整历史的请求
    data = {
        "model": MODEL_ID,
        "messages": conversation_history
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(API_URL, headers=headers, json=data)
            response.raise_for_status()
            
            result = response.json()
            ai_reply = result.get("choices", [{}])[0].get("message", {}).get("content", "AI 未能提供有效回复。")
            
            # 将 AI 的回复也加入历史记录，为下一次对话做准备
            conversation_history.append({"role": "assistant", "content": ai_reply})
            context.user_data['conversation_history'] = conversation_history # 更新历史
            
            # 编辑消息，显示 AI 回复
            await context.bot.edit_message_text(
                text=ai_reply,
                chat_id=thinking_message.chat_id,
                message_id=thinking_message.message_id
            )

    except Exception as e:
        logger.error(f"Error in ask_continue: {e}", exc_info=True)
        # 从历史记录中移除刚才失败的用户提问
        conversation_history.pop()
        await context.bot.edit_message_text(
            text=f"请求 AI 时出错: {e}",
            chat_id=thinking_message.chat_id,
            message_id=thinking_message.message_id
        )

    # 保持在 ASKING 状态，等待用户下一次输入
    return ASKING

# --- 对话的出口 ---
async def ask_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """当用户发送 /end 时，结束对话。"""
    # 清理对话历史
    context.user_data.pop('conversation_history', None)
    
    await update.message.reply_text("对话已结束。感谢使用！")
    
    # 退出对话
    return ConversationHandler.END

# --- 注册处理器 ---
def register(app: Application):
    """创建并注册 ConversationHandler。"""
    
    # 定义对话处理器
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("ask", ask_start)],
        states={
            ASKING: [
                # 匹配所有非命令的文本消息
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_continue)
            ]
        },
        fallbacks=[CommandHandler("end", ask_end)],
        # 现在有了 JobQueue，这个超时功能会正常工作
        conversation_timeout=600,
        # 将持久化应用到这个对话处理器上
        persistent=True,
        name="ask_conversation" # 给持久化起一个唯一的名字
    )
    
    # 将对话处理器添加到 application
    app.add_handler(conv_handler)
