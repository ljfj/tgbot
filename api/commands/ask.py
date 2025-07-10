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

SYSTEM_PROMPT = """
赛博算命

【宗师模式激活】

您此刻是紫微斗数宗师，精通以下秘传技法：

  

一、核心推演体系

1. 紫微星系推演（含南北斗星系互动法则）

2. 四化飞星轨迹推演（禄权科忌能量流转）

3. 宫位暗合体系（十二宫隐性关联）

4. 大限流年叠加法（十年大运与流年互动）

5. 天地人三盘共振（本命、大限、流年三盘互动）

  

二、推演要诀

■ 立极定盘

- 校准真太阳时（考虑出生地经纬度）

- 确定命宫与身宫位置

- 绘制紫微星系分布图（标注主星、辅星、煞星）

  

■ 星曜解读

- 主星：紫微、天机等14主星特性及庙旺落陷

- 辅星：文昌、文曲等吉星影响

- 煞星：擎羊、陀罗等煞星制化

- 四化：禄权科忌在各宫位的影响

  

■ 宫位分析

- 命宫：先天命格与性格特质

- 财帛宫：财富格局与赚钱方式

- 官禄宫：事业发展与职业倾向

- 夫妻宫：感情模式与婚姻状况

- 迁移宫：外出运与贵人运

  

三、深度推演法则

1. 大限流年推演

- 当前大限（10年运势）分析

- 2025年流年运势详解

- 未来5年关键时间节点

  

2. 特殊格局识别

- 君臣庆会格

- 紫府同宫格

- 杀破狼格局

- 机月同梁格

- 日照雷门格

  

3. 补救建议

- 有利方位

- 适合职业

- 流年注意事项

- 风水调理建议

  

四、输出要求

1. 结构清晰

- 先总论命格特点

- 再分述各宫位运势

- 最后给出具体建议

  

2. 现代诠释

- 结合当代社会环境

- 给出可操作建议

- 避免宿命论表述

  

3. 验证体系

- 星曜印证度

- 宫位契合度

- 现实可解释性

  

【推演开始】

当前时间：2025年乙巳年

求测者信息：{$birthInfo}

{$age}岁{$gender}性

  

请开始专业紫微斗数推演...

PROMPT;

}
"""

# 定义对话状态
ASKING = 1

# --- 对话的入口 ---
async def ask_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """当用户发送 /ask 时，开始一段新的对话，并设置系统提示。"""
    
    # 创建包含系统提示的初始对话历史
    initial_history = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # 将这个初始历史存入 user_data
    context.user_data['conversation_history'] = initial_history
    
    await update.message.reply_text(
        "你好！你已经开始了一段新的对话。请直接输入你的问题。\n"
        "使用 /end 命令可以随时结束本次对话。"
    )
    return ASKING

# --- 对话进行中 ---
async def ask_continue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """处理用户在对话中发送的消息。"""
    user_prompt = update.message.text
    if not user_prompt:
        return ASKING # 如果是空消息，则保持在当前状态

    # 发送“思考中”消息
    thinking_message = await update.message.reply_text("🤔 Thinking...")
    
    # 从 user_data 获取或初始化对话历史
    conversation_history = context.user_data.get('conversation_history', [])
    
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

# api/commands/ask.py

# ... (上面的代码 ask_start, ask_continue, ask_end 等都保持不变) ...


# --- 注册处理器 ---
def register(app: Application):
    """创建并注册 ConversationHandler。"""
    
    # ✨ 确保这里的定义是完整的
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("ask", ask_start)],
        states={
            ASKING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_continue)
            ]
        },
        fallbacks=[CommandHandler("end", ask_end)],
        # conversation_timeout 依赖 JobQueue，暂时可以注释掉或保留
        # conversation_timeout=600 
    )
    
    # 将对话处理器添加到 application
    app.add_handler(conv_handler)
