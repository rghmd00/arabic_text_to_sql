import os
from langchain_ollama import ChatOllama

# Inside Docker, this will be http://host.docker.internal:11434
# Locally, this will default to http://localhost:11434


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

def build_client() -> ChatOllama:
    return ChatOllama(
        model="qwen2.5-coder:3b", 
        temperature=0,
        base_url=OLLAMA_BASE_URL
    )

def build_translate_client() -> ChatOllama:
    return ChatOllama(
        model="qwen2.5:3b-instruct", 
        temperature=0,
        base_url=OLLAMA_BASE_URL
    )