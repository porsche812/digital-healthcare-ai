import gradio as gr

from service.chat_service import ChatService


class HealthcareChatbotApp:
    def __init__(self):
        self.chat_service = ChatService()

    def chat_wrapper(self, message, history):
        """Gradio ChatInterface 전용 래퍼: (message, history) -> 응답 문자열"""
        return self.chat_service.get_response(message, history)

    def create_ui(self):
        return gr.ChatInterface(
            fn=self.chat_wrapper,
            type="messages",  # history 를 dict(role/content) 형태로 받음(권장)
            title="🏥 디지털 헬스케어 전문 AI 챗봇 🏥",
            description="건강검진, 병원 예약, 복약 안내 등 궁금한 점을 물어보세요.",
            examples=[
                "검진 전날 물 마셔도 되나요?",
                "보험 청구 서류 알려줘",
                "수면 내시경 후 운전 가능한가요?",
            ],
        )
