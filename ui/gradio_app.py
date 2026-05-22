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
            title="🏥 디지털 헬스케어 AI 챗봇 🏥",
            description="내과 관련 질환의 증상·진단·치료·예방 등을 물어보세요. "
                        "(AI Hub 의료 질의응답 데이터 기반)",
            examples=[
                "급성 위장염은 어떻게 치료하나요?",
                "당뇨병 환자의 식이요법이 궁금해요",
                "고혈압은 어떻게 관리하나요?",
            ],
        )
