# api/kv_persistence.py
import json
from typing import Optional, Dict, Any, Tuple
from telegram.ext import BasePersistence, PersistenceInput
from vercel_kv import kv

class VercelKVPersistence(BasePersistence):
    """
    使用 Vercel KV 作为持久化后端的优化版本。
    确保所有数据在存入/取出时都被正确地序列化/反序列化。
    """
    def __init__(self):
        super().__init__(store_data=PersistenceInput(bot_data=True, chat_data=True, user_data=True))

    async def _get_json_data(self, key: str) -> Dict:
        """从 KV 获取并解析 JSON 数据的辅助函数。"""
        data = await kv.get(key)
        return json.loads(data) if data else {}

    async def _set_json_data(self, key: str, data: Dict) -> None:
        """将 JSON 数据写入 KV 的辅助函数。"""
        await kv.set(key, json.dumps(data))

    async def get_bot_data(self) -> Dict[int, Any]:
        return await self._get_json_data("bot_data")

    async def update_bot_data(self, data: Dict[int, Any]) -> None:
        await self._set_json_data("bot_data", data)

    async def get_chat_data(self) -> Dict[int, Any]:
        data = await self._get_json_data("chat_data")
        return {int(k): v for k, v in data.items()}

    async def update_chat_data(self, data: Dict[int, Any]) -> None:
        await self._set_json_data("chat_data", data)

    async def get_user_data(self) -> Dict[int, Any]:
        data = await self._get_json_data("user_data")
        return {int(k): v for k, v in data.items()}

    async def update_user_data(self, data: Dict[int, Any]) -> None:
        await self._set_json_data("user_data", data)

    async def get_callback_data(self) -> Optional[Dict]:
        return None 

    async def update_callback_data(self, data: Dict) -> None:
        pass

    async def get_conversations(self, name: str) -> Dict:
        """获取对话状态，并正确地将字符串 key 转换回元组。"""
        data = await self._get_json_data(f"conversation_{name}")
        # ✨ 关键优化：使用 json.loads 将字符串 key'["12345"]' 转换回列表，再转成元组
        return {tuple(json.loads(k)): v for k, v in data.items()}

    async def update_conversation(
        self, name: str, key: Tuple[int, ...], new_state: Optional[object]
    ) -> None:
        """更新对话状态，并确保 key 被安全地序列化为字符串。"""
        conversations = await self.get_conversations(name)
        # ✨ 关键优化：使用 json.dumps 将元组 key (12345,) 转换成字符串 '["12345"]'
        str_key = json.dumps(list(key))
        
        if new_state is None:
            conversations.pop(str_key, None)
        else:
            conversations[str_key] = new_state
        
        # 将整个对话字典写回 KV
        # 注意：这里的 conversations 的 key 仍然是元组，我们需要在写入前转换它们
        data_to_write = {json.dumps(list(k)): v for k, v in conversations.items()}
        await self._set_json_data(f"conversation_{name}", data_to_write)

    async def flush(self) -> None:
        pass
