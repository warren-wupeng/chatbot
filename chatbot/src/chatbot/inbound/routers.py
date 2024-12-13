from fastapi import APIRouter
from datetime import datetime
import json
from typing import Annotated


from pydantic import BaseModel

from chatbot.domain import BehaviorReport, ChatMessage, ChatMessageView, UserRepo
from chatbot.inbound.depends import get_user_repo
from chatbot.inbound.depends import get_llm
from chatbot.outbound import LLM
from chatbot.application import (
    _gen_ai_reply, _gen_ai_reply_advanced, _get_ai_chat_response
)
from chatbot.domain import ChatResponse
from fastapi import Depends

apiRouter = APIRouter()


class Body(BaseModel):
    message: str


@apiRouter.post("/api/user/{user_name}/ai/chat/response",
          response_model=ChatResponse,
          responses={401: {"description": "Too many requests"}})
async def get_ai_chat_response(
        user_name: str, body: Body,
        user_repo: Annotated[UserRepo, Depends(get_user_repo)],
        llm: Annotated[LLM, Depends(get_llm)]):
    return _get_ai_chat_response(
        user_name, body.message, user_repo, llm, _gen_ai_reply, ''
    )


@apiRouter.post("/api/user/{user_name}/ai/chat/response/advanced",
          response_model=ChatResponse,
          responses={401: {"description": "Too many requests"}})
async def get_ai_chat_response_advanced(
        user_name: str, body: Body,
        user_repo: Annotated[UserRepo, Depends(get_user_repo)],
        llm: Annotated[LLM, Depends(get_llm)]):
    return _get_ai_chat_response(
        user_name, body.message, user_repo, llm, _gen_ai_reply_advanced, ''
    )


@apiRouter.get("/api/user/{user_name}/ai/chat/history",
         response_model=list[ChatMessageView])
async def get_ai_chat_histories(
        user_name: str, last_n: int,
        user_repo: Annotated[UserRepo, Depends(get_user_repo)]):
    user = user_repo.get(user_name)
    chat_histories = user.chat_histories.find(last_n=last_n)
    return [
        ChatMessageView(type=chat.type, text=chat.text)
        for chat in chat_histories
    ]


class ChatStatusToday(BaseModel):
    user_name: str
    chat_cnt: int


@apiRouter.get("/api/user/{user_name}/ai/chat/status/today",
         response_model=ChatStatusToday)
async def get_ai_chat_status_today(
        user_name: str, user_repo: Annotated[UserRepo, Depends(get_user_repo)]):
    user = user_repo.get(user_name)
    today = datetime.now().date()
    today_chat_histories = user.chat_histories.find(
        types_in=['user', 'ai'],
        since=datetime(today.year, today.month, today.day)
    )
    return ChatStatusToday(
        user_name=user_name, chat_cnt=len(today_chat_histories))


@apiRouter.post("/api/user/{user_name}/behavior/report",
          response_model=BehaviorReport)
async def get_user_behavior_report(
        user_name: str,
        user_repo: Annotated[UserRepo, Depends(get_user_repo)],
        llm: Annotated[LLM, Depends(get_llm)]):
    user = user_repo.get(user_name)
    chat_history = user.chat_histories.find(types_in=['user'])
    system_prompt = """Generate a report of the user behavior based on the 
    chat history. report the user's most common topics and active hours.
    response format:
    ```The user is mostly interested in [topic1], [topic2], [topic3]...
    The user is most active at from [hh:mm] to [hh:mm]```

    chat history: 
    """
    content = system_prompt + "\n".join([
        json.dumps({'text': m.text, 'time': m.time.isoformat()})
        for m in chat_history
    ])
    messages = [
        ChatMessage(type="system", text=content, time=datetime.now())
    ]
    report = llm.get_chat_completion(messages)
    return BehaviorReport(user_name=user_name, report=report)
