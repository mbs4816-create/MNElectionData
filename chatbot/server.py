"""FastAPI wrapper around the Minnesota election chatbot."""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from .bot import ElectionChatbot


app = FastAPI(title="Minnesota Election Chatbot")
chatbot = ElectionChatbot()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    return ChatResponse(response=chatbot.reply(request.message))
