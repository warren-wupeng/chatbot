from chatbot.outbound import LLM, MONGO_CLIENT, MongoUserRepo


def get_user_repo():
    return MongoUserRepo(MONGO_CLIENT)


def get_llm():
    return LLM()
