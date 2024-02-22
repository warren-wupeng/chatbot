import os
from fastapi import FastAPI
from pydantic import BaseModel
import pymongo
import requests
import json

OPENROUTER_API_KEY=os.environ.get("OPENROUTER_API_KEY")
YOUR_SITE_URL=os.environ.get("YOUR_SITE_URL")
YOUR_APP_NAME="chatbot"
MONGO_DB_PASSWORD=os.environ.get("MONGO_DB_PASSWORD")

MONGO_DB_URL=f"mongodb+srv://wupeng0059:{MONGO_DB_PASSWORD}@cluster0.wzekc0u.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
print(MONGO_DB_URL)
mongo_client = pymongo.MongoClient(MONGO_DB_URL)
app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

class Body(BaseModel):
    message: str

@app.post("/user/{user_name}/ai/chat/response")
async def get_ai_chat_response(user_name: str, body: Body):


    db = mongo_client["Cluster0"]
    users = db["user"]
    user = users.find_one({"name": user_name})
    if user is None:
        users.insert_one({"name": user_name, "chat_histories": []})
        chat_histories = []
    else:
        chat_histories = user["chat_histories"]
    response = requests.post(
    url="https://openrouter.ai/api/v1/chat/completions",
    
    headers={
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": f"{YOUR_SITE_URL}", 
        "X-Title": f"{YOUR_APP_NAME}", 
    },
    data=json.dumps({
        "model": "mistralai/mistral-7b-instruct:free",
        "transforms": ["middle-out"],
        "messages": [
            {"role": "assistant" if m['type'] == 'ai' else 'user'} 
            for m in chat_histories
        ]+[
        {"role": "user", "content": body.message}
        ]
    })
    )
    res_json = response.json()
    ai_reply = res_json["choices"][0]["message"]["content"]

    chat_histories.append({"type": "user", "content": body.message})
    chat_histories.append({"type": "ai", "content": ai_reply})
    users.update_one({"name": user_name}, {"$set": {"chat_histories": chat_histories}})
    
    return {"response": ai_reply}

@app.get("/user/{user_name}/ai/chat/histories")
async def get_ai_chat_histories(
    user_name: str
    ):
    return {"message": "Hello World"}

def main():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()