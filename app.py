import time
import gradio as gr
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# .env 파일 로드
load_dotenv()

# llm 객체 생성
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)