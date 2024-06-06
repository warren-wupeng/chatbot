import abc
from pydantic import BaseModel

from datetime import datetime, timedelta
from typing import Literal, Optional


class ChatMessage(BaseModel):
    time: datetime
    type: Literal["user", "ai", "system"]
    text: str



class UserMessage(ChatMessage):
    type: Literal["user"] = "user"


class AIReply(ChatMessage):
    type: Literal["ai"] = "ai"


class SystemMessage(ChatMessage):
    type: Literal["system"] = "system"


class Dialog(BaseModel):
    user_message: UserMessage
    ai_reply: AIReply

class UserChatHistories(abc.ABC):

    @abc.abstractmethod
    def add_dialog(self, dialog: Dialog):
        pass
    
    @abc.abstractmethod
    def find(
        self, last_n: int = 1000,
        types_in: list[str] = ['user', 'ai'],
        since: Optional[datetime] = None
    ) -> list[ChatMessage]:
        pass

class User:

    def __init__(self, user_name: str, user_chat_histories: UserChatHistories):
        self.user_name = user_name
        self.chat_histories = user_chat_histories

    def add_dialog(self, dialog: Dialog):
        self.should_no_more_then_3_user_message_in_30_seconds()
        self.should_no_more_then_30_user_message_in_24_hours()
        self.chat_histories.add_dialog(dialog)

    def should_no_more_then_3_user_message_in_30_seconds(self):
        last_30_seconds = datetime.now() - timedelta(seconds=30)
        user_messages = self.chat_histories.find(
            types_in=['user'], since=last_30_seconds)
        if len(user_messages) >= 3:
            raise self.TooManyRequests(
                'Too many requests in 30 seconds. Please try again later.'
            )

    def should_no_more_then_30_user_message_in_24_hours(self):
        today = datetime.now().date()
        today_chat_histories = self.chat_histories.find(
            types_in=['user'], since=datetime(today.year, today.month, today.day))
        if len(today_chat_histories) >= 30:
            raise self.TooManyRequests(
                'Too many requests in 24 hours. Please try again later.'
            )

    class TooManyRequests(Exception):
        pass



class UserRepo(abc.ABC):

    @abc.abstractmethod
    def get(self, user_name: str) -> User:
        pass

