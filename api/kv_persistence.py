# api/kv_persistence.py
import json
from typing import Optional, Dict, Any, Tuple, cast
from telegram.ext import BasePersistence, PersistenceInput
from vercel_kv import kv

class VercelKVPersistence(BasePersistence):
    """使用 Vercel KV 作为持久化后端的类。"""

    def __init__(self):
        super().__init__(store_data=PersistenceInput(bot_data=True, chat_data=True, user_data=True))
        
    async def get_bot_data(self) -> Dict[int, Any]:
        data = await kv.get("bot_data")
        return json.loads(data) if data else {}

    async def update_bot_data(self, data: Dict[int, Any]) -> None:
        await kv.set("bot_data", json.dumps(data))

    async def get_chat_data(self) -> Dict[int, Any]:
        data = await kv.get("chat_data")
        return {int(k): v for k, v in json.loads(data).items()} if data else {}

    async def update_chat_data(self, data: Dict[int, Any]) -> None:
        await kv.set("chat_data", json.dumps(data))

    async def get_user_data(self) -> Dict[int, Any]:
        data = await kv.get("user_data")
        return {int(k): v for k, v in json.loads(data).items()} if data else {}

    async def update_user_data(self, data: Dict[int, Any]) -> None:
        await kv.set("user_data", json.dumps(data))

    async def get_callback_data(self) -> Optional[Dict]:
        return None # 简单起见，我们暂时不持久化 callback_data

    async def update_callback_data(self, data: Dict) -> None:
        pass # 简单起见，我们暂时不持久化 callback_data

    async def get_conversations(self, name: str) -> Dict:
        data = await kv.get(f"conversation_{name}")
        if not data:
            return {}
        # Redis (KV) 存的是字符串，需要把 key 转回元组
        parsed_data = json.loads(data)
        return {tuple(json.loads(k)): v for k, v in parsed_data.items()}

    async def update_conversation(
        self, name: str, key: Tuple[int, ...], new_state: Optional[object]
    ) -> None:
        conversations = await self.get_conversations(name)
        # 使用 JSON 序列化的元组作为 key
        str_key = json.dumps(key)
        if new_state is None:
            conversations.pop(str_key, None)
        else:
            conversations[str_key] = new_state
        
        # Redis (KV) 存的是字符串，需要把 key 转回元组
        await kv.set(f"conversation_{name}", json.dumps(conversations))

    async def flush(self) -> None:
        # Vercel KV 每次 set 都是即时写入的，所以不需要 flush
        pass
