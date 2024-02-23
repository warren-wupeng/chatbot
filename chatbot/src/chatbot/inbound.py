from datetime import datetime
import json
from typing import Annotated, Callable

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from chatbot.domain import AIReply, ChatMessage, Dialog, SystemMessage, User, UserMessage, UserRepo
from chatbot.outbound import LLM, MONGO_CLIENT, MongoUserRepo

app = FastAPI()

def get_user_repo():
    return MongoUserRepo(MONGO_CLIENT)

def get_llm():
    return LLM()

@app.get("/")
async def health_check():
    return {"message": "Hello World"}

class ChatResponse(BaseModel):
    response: str

class Body(BaseModel):
    message: str


@app.post("/user/{user_name}/ai/chat/response", 
        response_model=ChatResponse, 
        responses={401: {"description": "Too many requests"}})
async def get_ai_chat_response(
    user_name: str, body: Body, 
    user_repo: Annotated[UserRepo, Depends(get_user_repo)],
    llm: Annotated[LLM, Depends(get_llm)]):
    return _get_ai_chat_response(
        user_name, body.message, user_repo, llm, _gen_ai_reply
    )

@app.post("/user/{user_name}/ai/chat/response/advanced",
          response_model=ChatResponse,
          responses={401: {"description": "Too many requests"}})
async def get_ai_chat_response_advanced(
    user_name: str, body: Body,
    user_repo: Annotated[UserRepo, Depends(get_user_repo)],
    llm: Annotated[LLM, Depends(get_llm)]):
    return _get_ai_chat_response(
        user_name, body.message, user_repo, llm, _gen_ai_reply_advanced
    )
 
class ChatMessageView(BaseModel):
    type: str
    text: str


@app.get("/user/{user_name}/ai/chat/history",
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

@app.get("/user/{user_name}/ai/chat/status/today",
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

class BehaviorReport(BaseModel):
    user_name: str
    report: str

@app.post("/user/{user_name}/behavior/report",
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
        json.dumps({'text': m.text, 'time': m.time.isoformat() })
        for m in chat_history
    ])
    messages = [
        ChatMessage(type="system", text=content, time=datetime.now())
    ]
    report = llm.get_chat_completion(messages)
    return BehaviorReport(user_name=user_name, report=report)

@app.exception_handler(User.TooManyRequests)
async def too_many_requests_exception_handler(request, exc):
    return JSONResponse(
        status_code=401,
        content={"detail": str(exc)}
    )

def _get_ai_chat_response(
        user_name: str, message: str, 
        user_repo: UserRepo,
        llm: LLM,
        gen_ai_reply_method: Callable[[list[ChatMessage], LLM], str]):
    user = user_repo.get(user_name)
    chat_history = user.chat_histories.find()
    user_message = UserMessage(text=message, time=datetime.now())
    chat_history.append(user_message)
    ai_reply_text = gen_ai_reply_method(chat_history, llm)
    ai_reply = AIReply(text=ai_reply_text, time=datetime.now())
    dialog = Dialog(user_message=user_message, ai_reply=ai_reply)
    user.add_dialog(dialog)
    return ChatResponse(response=ai_reply.text)

def _gen_ai_reply(chat_histories: list[ChatMessage], llm: LLM) -> str:
    result = llm.get_chat_completion(chat_histories)
    return result

def _gen_ai_reply_advanced(chat_histories: list[ChatMessage], llm: LLM) -> str:
    sentiment = _analyse_sentiment(chat_histories[-1].text, llm)
    system_content = f"make the repsponse suitable for a user with {sentiment} sentiment"
    chat_histories.append(
        SystemMessage(text=system_content, time=datetime.now())
    )
    result = llm.get_chat_completion(chat_histories)
    return result

def _analyse_sentiment(text: str, llm: LLM) -> str:
    system_prompt = """Analyse the sentiment of the query given by the user
    return the sentiment as one word: positive, negative or neutral"""
    messages = [
        ChatMessage(type="system", text=system_prompt, time=datetime.now()),
        ChatMessage(type="user", text=text, time=datetime.now())
    ]
    result = llm.get_chat_completion(messages)
    return result

def main():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()