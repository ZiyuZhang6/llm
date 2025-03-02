import uvicorn
from fastapi import FastAPI

from llm_research_assistant.routes import users, papers, chats, auth, chat_rag, email

app = FastAPI(title="LLM Research Assistant API", version="0.1.0")

app.include_router(users.router)
app.include_router(papers.router)
app.include_router(chats.router)
app.include_router(auth.router)
app.include_router(chat_rag.router)
app.include_router(email.router)


@app.get("/")
def root():
    return {"message": "Welcome to LLM Research Assistant API"}


if __name__ == "__main__":
    uvicorn.run(
        "llm_research_assistant.main:app", host="0.0.0.0", port=8000, reload=True
    )
