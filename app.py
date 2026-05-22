from ui.gradio_app import HealthcareChatbotApp

if __name__ == "__main__":
    # 1. UI 앱 인스턴스 생성 (데이터 로드 + 인덱스 빌드/로드가 여기서 일어남)
    app = HealthcareChatbotApp()

    # 2. UI 레이아웃 구성
    demo = app.create_ui()

    # 3. 서버 실행 (공개 링크를 원하시면 launch(share=True))
    demo.launch()
