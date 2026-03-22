import os
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from config import settings

class FAQRetriever:
    def __init__(self, faq_data):
        # 1. 임베딩 모델 초기화
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=settings.OPENAI_API_KEY,
            model=settings.EMBEDDING_MODEL_NAME
        )
        
        # 2. 로컬에 저장된 벡터스토어가 있으면 불러오고, 없으면 새로 생성
        if os.path.exists(settings.VECTOR_STORE_PATH):
            self.vectorstore = FAISS.load_local(
                settings.VECTOR_STORE_PATH, 
                self.embeddings, 
                allow_dangerous_deserialization=True # 로컬 파일이므로 안전함 허용
            )
        else:
            # FAQ 데이터를 LangChain Document 객체로 변환 (노트북 사이클 1)
            documents = []
            for item in faq_data:
                content = f"Q: {item['question']}\nA: {item['answer']}"
                meta = {
                    "id": item["id"], 
                    "category": item["category"]
                }
                documents.append(Document(page_content=content, metadata=meta))
            
            # FAISS 벡터 스토어 생성 및 로컬 저장 (노트북 사이클 3)
            self.vectorstore = FAISS.from_documents(documents, self.embeddings)
            self.vectorstore.save_local(settings.VECTOR_STORE_PATH)
    
    def search(self, query: str, top_k=2):
        # 노트북 사이클 4: similarity_search를 통해 Document 리스트 반환
        return self.vectorstore.similarity_search(query, k=top_k)