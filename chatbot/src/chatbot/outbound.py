import json
from typing import Optional
import os
import pymongo

from datetime import datetime
from chatbot.domain import ChatMessage, Dialog, User, UserChatHistories, UserRepo
import requests

MONGO_DB_URL=os.environ.get("MONGO_DB_URL")
print(MONGO_DB_URL)
MONGO_CLIENT = pymongo.MongoClient(MONGO_DB_URL)

class MongoUserChatHistories(UserChatHistories):

    def __init__(self, user_name: str, client: pymongo.MongoClient):
        self.user_name = user_name
        self.db = client["Cluster0"]
        self.collection = self.db["userChatHistories"]

    def add_dialog(self, dialog: Dialog):
        self.collection.insert_many([
            {
                "user_name": self.user_name,
                "type": dialog.user_message.type,
                "text": dialog.user_message.text,
                "time": dialog.user_message.time
            },
            {
                "user_name": self.user_name,
                "type": dialog.ai_reply.type,
                "text": dialog.ai_reply.text,
                "time": dialog.ai_reply.time
            }
        ])
    def find(
            self, last_n: int = 1000,
            types_in: list[str] = ['user', 'ai'],
            since: Optional[datetime] = None
        ) -> list[ChatMessage]:
        filters = {"user_name": self.user_name, "type": {"$in": types_in}}
        if since:
            filters["time"] = {"$gte": since}
        chat_histories = list(self.collection.find(
            filters, sort=[("time", pymongo.DESCENDING)], limit=last_n
        ))
        chat_histories.reverse()
        return [
            ChatMessage(type=chat["type"], text=chat["text"], time=chat["time"])
            for chat in chat_histories
        ]

class MongoUserRepo(UserRepo):
    
    def __init__(self, client: pymongo.MongoClient):
        self.db = client["Cluster0"]
        self.collection = self.db["users"]

    def get(self, user_name: str) -> User:
        user_chat_histories = MongoUserChatHistories(user_name, MONGO_CLIENT)
        return User(user_name, user_chat_histories)
    
class LLM:
    OPENROUTER_API_KEY=os.environ.get("OPENROUTER_API_KEY")
    YOUR_SITE_URL=os.environ.get("YOUR_SITE_URL")
    YOUR_APP_NAME="chatbot"
    URL = "https://openrouter.ai/api/v1/chat/completions"
    HEADERS = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": f"{YOUR_SITE_URL}",
        "X-Title": f"{YOUR_APP_NAME}",
    }

    def _to_llm_format(self, chat_histories: list[ChatMessage]):
        messages = [
            {
                "role": "assistant" if m.type == 'ai' else m.type,
                "content": m.text
            }
            for m in chat_histories
        ]
        for m in messages:
            print(m)
        return messages


    def get_chat_completion(self, chat_messages: list[ChatMessage]) -> str:
        messages = self._to_llm_format(chat_messages)
        # model = "mistralai/mistral-7b-instruct:free"
        model = "openai/gpt-3.5-turbo"
        response = requests.post(
            url=self.URL,
            headers=self.HEADERS,
            data=json.dumps({
                "model": model,
                "transforms": ["middle-out"],
                "messages": messages
            })
        )
        res_json = response.json()
        result = res_json["choices"][0]["message"]["content"]
        return result