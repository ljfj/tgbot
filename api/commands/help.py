# api/commands/help.py
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """显示所有可用命令的帮助信息。"""
    help_text = (
        "/start - 开始与机器人对话\n"
        "/help - 显示此帮助信息\n"
        "/ask - 开始一段与 AI 的连续对话\n"
        "/end - 结束当前的 AI 对话\n"  # <-- 手动添加这一行
        "/t - 翻译文本内容"
    )
    await update.message.reply_text(help_text)

def register(app: Application):
    """将 /help 命令处理器注册到 application"""
    app.add_handler(CommandHandler("help", help_command))
