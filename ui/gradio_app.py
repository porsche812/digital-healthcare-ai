import gradio as gr
from service.chat_service import ChatService

class HealthcareChatbotApp:
    def __init__(self):
        self.chat_service = ChatService()

    def chat_wrapper(self, message, history):
        """Gradio 전용 래퍼 함수"""
        # Gradio의 ChatInterface는 (message, history) 두 인자를 필수로 요구함.
        # 우리 서비스는 단발성 응답을 하므로 message만 서비스 레이어에 전달함.
        return self.chat_service.get_response(message, history)
    
    def create_ui(self):
        """Gradio UI 레이아웃 생성"""
        # [설계 의도] 사용자가 보기 편한 인터페이스 설정과 예시 질문을 배치함
        demo = gr.ChatInterface(
            fn=self.chat_wrapper, # 채팅창에 입력 시 호출될 함수 연결
            title="🏥 디지털 헬스케어 전문 AI 챗봇 🏥",
            description="건강검진, 병원 예약, 복약 안내 등 궁금한 점을 물어보세요.",
            examples=[                         # 사용자가 클릭해서 바로 물어볼 수 있는 예시
                "검진 전날 물 마셔도 되나요?",
                "보험 청구 서류 알려줘",
                "수면 내시경 후 운전 가능한가요?"
            ],
            # theme="soft"
        )
        return demo