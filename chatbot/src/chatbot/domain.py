from __future__ import annotations
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


system_prompt_adl = """你是一个具有阿德勒哲学思想的心理咨询师。以下是你的一些核心观点：

1. 我们的不幸都是自己的选择
2. 一切烦恼都来自人际关系
3. 让干涉你生活的人见鬼去
4. 要有被讨厌的勇气
5. 认真的人生活在当下

请根据以上观点,运用苏格拉底式提问法与用户交谈,让用户自己找到答案。"""
system_prompt_cbt = """你是一个具有认知行为疗法思想的心理咨询师。以下是你帮助用户解决问题的方法：
CBT认知行为疗法,诊断用户的心理困境和具体在职业生活中的反应情景,找到引发不良情绪的认知路径。
1、聆听用户的困境,确定他在情景中的反应。
2,根据反应问询,情景中的哪些特征触发了他的第一信念,
3,跟随第一信念,问询这个信念背后用户产生了怎样的感受和链式反应,确定中间信念和自动化反应
4,呈现这个过程,让用户了解到自己的认知回路
5,让用户选择一个自己更想要的反应和感受,即新的信念
6,让用户根据新信念,对应之前的认知回路上的各个环节,替代对应的子信念并完成新的认知闭环。
7,为巩固用户的替代效果,邀请用户在情景环境中设置一个提示,
8,制定一个7天练习计划,以“我是一个XX(新信念)的人+每日行动记录📝为练习的格式。
9,等待用户提交7天的练习成果并检验
请根据以上方法,引导用户一步一步地完成以上过程,与用户交谈"""


class ChatResponse(BaseModel):
    response: str


class ChatMessageView(BaseModel):
    type: str
    text: str


class BehaviorReport(BaseModel):
    user_name: str
    report: str


class ServiceNavigatorFSM(abc.ABC):

    _state: ServiceNavigatorState

  
    def lifeExplorerIntent(self):
        self._state.lifeExplorerIntent(self)
    
    def positiveIntent(self):
        self._state.positiveIntent(self)
    
    def negativeIntent(self):
        self._state.negativeIntent(self)
    
    def talentCousultingIntent(self):
        self._state.talentCousultingIntent(self)

    def cognitivePractiveIntent(self):
        self._state.cognitivePractiveIntent(self)

    def astraNorlandStoryIntent(self):
        self._state.astraNorlandStoryIntent(self)
    
    def movieIntent(self):
        self._state.movieIntent(self)
    
    def setState(self, state: ServiceNavigatorState):
        self._state = state


    @abc.abstractmethod
    def chatOpening(self):
        pass

    @abc.abstractmethod
    def introduceLifeExplorer(self):
        pass

    @abc.abstractmethod
    def getStartedLifeExplorer(self):
        pass

    @abc.abstractmethod
    def otherOptions(self):
        pass

    @abc.abstractmethod
    def introduceTalentConsulting(self):
        pass

    


class ServiceNavigatorState(abc.ABC):

    @abc.abstractmethod
    def lifeExplorerIntent(self, fsm: ServiceNavigatorFSM):
        pass

    @abc.abstractmethod
    def positiveIntent(self, fsm: ServiceNavigatorFSM):
        pass

    @abc.abstractmethod
    def negativeIntent(self, fsm: ServiceNavigatorFSM):
        pass

    @abc.abstractmethod
    def talentCousultingIntent(self, fsm: ServiceNavigatorFSM):
        pass

    @abc.abstractmethod
    def cognitivePractiveIntent(self, fsm: ServiceNavigatorFSM):
        pass
    
    @abc.abstractmethod
    def astraNorlandStoryIntent(self, fsm: ServiceNavigatorFSM):
        pass

    @abc.abstractmethod
    def movieIntent(self, fsm: ServiceNavigatorFSM):
        pass


class ServiceNavigatorFSMImpl(ServiceNavigatorFSM):