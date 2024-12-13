
from typing import Annotated
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi import Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from chatbot.application import _gen_ai_reply_coaching, _get_ai_chat_response
from chatbot.domain import ChatMessageView, User, UserRepo, system_prompt_cbt
from chatbot.inbound.depends import get_llm, get_user_repo
from chatbot.outbound import LLM
from .routers import apiRouter

app = FastAPI()
app.include_router(apiRouter)


def render_index_page(
        request: Request, user_name: str, messages: list[ChatMessageView]
):
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


@app.post('/get-chat-history', response_class=HTMLResponse)
async def form_post(
    request: Request,
    user_repo: Annotated[UserRepo, Depends(get_user_repo)],
):
    form = await request.form()
    user_name = form['user_name']
    if not isinstance(user_name, str):
        return JSONResponse(
            status_code=400, content={"message": "Invalid user name"}
        )
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


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
