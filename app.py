from ui.gradio_app import HealthcareChatbotApp

if __name__ == "__main__":

    # 1. UI 앱 인스턴스 생성
    app = HealthcareChatbotApp()

    # 2. UI 레이아웃 구성
    demo = app.create_ui()

    # 3. 서버 실행 (공개 링크를 원하시면 share=True 추가)
    demo.launch()

