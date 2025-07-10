# config.py
import os

# --- Telegram Bot Configuration ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# --- AI API Configuration ---
API_KEY = os.getenv("AI_TOKEN")

# ✨ 读取 API_URL 和 MODEL_ID 环境变量
# 如果 Vercel 里设置了，就用 Vercel 的值；否则，就用 " " 引号里的默认值。
API_URL = os.getenv(
    "AI_API_URL", 
    "https://api.groq.com/openai/v1/chat/completions"
)
MODEL_ID = os.getenv(
    "AI_MODEL_ID", 
    "llama3-8b-8192"
)

# --- 检查关键配置是否缺失 ---
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN not configured. Please set it as an environment variable.")

if not API_KEY:
    raise ValueError("AI_TOKEN (for API_KEY) not configured. Please set it as an environment variable.")
