from chatbot.domain import (
    AIReply, ChatMessage, Dialog, SystemMessage, UserMessage, UserRepo, 
    ChatResponse
)
from chatbot.outbound import LLM

from datetime import datetime, timezone
from typing import Callable


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


def _analyse_sentiment(text: str, llm: LLM) -> str:
    system_prompt = """Analyse the sentiment of the query given by the user
    return the sentiment as one word: positive, negative or neutral"""
    messages = [
        ChatMessage(type="system", text=system_prompt, time=datetime.now()),
        ChatMessage(type="user", text=text, time=datetime.now())
    ]
    result = llm.get_chat_completion(messages)
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
