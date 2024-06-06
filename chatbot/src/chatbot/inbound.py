from datetime import datetime, timezone
import json
from typing import Annotated, Callable

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from chatbot.domain import AIReply, ChatMessage, Dialog, SystemMessage, User, UserMessage, UserRepo
from chatbot.outbound import LLM, MONGO_CLIENT, MongoUserRepo

app = FastAPI()

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
def get_user_repo():
    return MongoUserRepo(MONGO_CLIENT)

def get_llm():
    return LLM()

class ChatMessageView(BaseModel):
    type: str
    text: str

def render_index_page(request: Request, user_name: str, messages: list[ChatMessageView]):
    return templates.TemplateResponse(
        name='index.html', 
        context={
            "request": request, "user_name": user_name, "messages": messages
        }
    )

@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    return render_index_page(request, "来访者", [])




templates = Jinja2Templates(directory="templates")

class ChatResponse(BaseModel):
    response: str

class Body(BaseModel):
    message: str

@app.post('/get-chat-history', response_class=HTMLResponse)
async def form_post(
    request: Request, 
    user_repo: Annotated[UserRepo, Depends(get_user_repo)],
    ):
    form = await request.form()
    user_name = form['user_name']
    if not isinstance(user_name, str):
        return JSONResponse(status_code=400, content={"message": "Invalid user name"})
    user = user_repo.get(user_name)

    chat_histories = user.chat_histories.find(last_n=10)
    messages = [
        ChatMessageView(type=chat.type, text=chat.text)
        for chat in chat_histories
    ]
    messages.insert(0, ChatMessageView(
        type="ai", 
        text=f"你好,{user_name},我是你的个人成长教练,有什么问题可以帮你解答吗？"
    ))
    return render_index_page(request, user_name, messages)

@app.post("/send-message")
async def send_message(
    request: Request,
    user_repo: Annotated[UserRepo, Depends(get_user_repo)],
    llm: Annotated[LLM, Depends(get_llm)]):

    form = await request.form()
    user_name = form['user_name']
    if not isinstance(user_name, str):
        return JSONResponse(
            status_code=400, content={"message": "Invalid user name"})
    message = form['message']
    if not isinstance(message, str):
        return JSONResponse(
            status_code=400, content={"message": "Invalid message"})

    _get_ai_chat_response(
        user_name=user_name, 
        message=message, 
        user_repo=user_repo, 
        llm=llm, 
        gen_ai_reply_method=_gen_ai_reply_coaching, 
        system_prompt=system_prompt_cbt
    )
    user = user_repo.get(user_name)
    chat_histories = user.chat_histories.find(last_n=10)
    messages = [
        ChatMessageView(type=chat.type, text=chat.text)
        for chat in chat_histories
    ]
    return render_index_page(request, user_name, messages)

@app.post("/user/{user_name}/ai/chat/response", 
        response_model=ChatResponse, 
        responses={401: {"description": "Too many requests"}})
async def get_ai_chat_response(
    user_name: str, body: Body, 
    user_repo: Annotated[UserRepo, Depends(get_user_repo)],
    llm: Annotated[LLM, Depends(get_llm)]):
    return _get_ai_chat_response(
        user_name, body.message, user_repo, llm, _gen_ai_reply, ''
    )

@app.post("/user/{user_name}/ai/chat/response/advanced",
          response_model=ChatResponse,
          responses={401: {"description": "Too many requests"}})
async def get_ai_chat_response_advanced(
    user_name: str, body: Body,
    user_repo: Annotated[UserRepo, Depends(get_user_repo)],
    llm: Annotated[LLM, Depends(get_llm)]):
    return _get_ai_chat_response(
        user_name, body.message, user_repo, llm, _gen_ai_reply_advanced, ''
    )
 

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

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )

def _get_ai_chat_response(
        user_name: str, message: str, 
        user_repo: UserRepo,
        llm: LLM,
        gen_ai_reply_method: Callable[[list[ChatMessage], LLM, str], str],
        system_prompt: str):
    user = user_repo.get(user_name)
    chat_history = user.chat_histories.find()
    user_message = UserMessage(text=message, time=datetime.now(timezone.utc))
    chat_history.append(user_message)
    ai_reply_text = gen_ai_reply_method(chat_history, llm, system_prompt)
    ai_reply = AIReply(text=ai_reply_text, time=datetime.now())
    dialog = Dialog(user_message=user_message, ai_reply=ai_reply)
    user.add_dialog(dialog)
    return ChatResponse(response=ai_reply.text)

def _gen_ai_reply(
        chat_histories: list[ChatMessage], llm: LLM, system_prompt: str = ''
        ) -> str:
    result = llm.get_chat_completion(chat_histories)
    return result


def _gen_ai_reply_advanced(
        chat_histories: list[ChatMessage], llm: LLM, system_prompt: str = ''
        ) -> str:
    sentiment = _analyse_sentiment(chat_histories[-1].text, llm)
    system_content = f"make the repsponse suitable for a user with {sentiment} sentiment"
    chat_histories.append(
        SystemMessage(text=system_content, time=datetime.now())
    )
    result = llm.get_chat_completion(chat_histories)
    return result

def _gen_ai_reply_coaching(
        chat_histories: list[ChatMessage], llm: LLM, system_prompt: str) -> str:

    chat_histories.insert(
        0, SystemMessage(text=system_prompt, time=datetime.now())
    )
    chat_histories.append(
        SystemMessage(text="提供AI的下一个回答", time=datetime.now())
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
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()