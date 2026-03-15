class FAQRetriever:
    
    # 생성자: 클래스가 생성될 때 호출
    def __init__(self, faq_data):
        # 외부(Repository)에서 가져온 FAQ 리스트를 인스턴스 변수에 저장하여 클래스 내부에서 계속 사용합니다.
        self.faq_data = faq_data
    
    # 핵심 검색 메서드: 질문(query)을 받아 결과 리스트를 반환
    def search(self, query: str, top_k = 2):

        # 빈 리스트 생성
        results = []

        # 사용자 질문을 공백 기준으로 자름
        query_tokens = query.split()

        # 데이터베이스(리스트)에 있는 모든 FAQ를 꺼내서 검사
        for faq in self.faq_data:

            # score 초기화
            score = 0

            # FAQ 데이터에 미리 정의된 핵심 키워드 대조
            for keyword in faq['keywords']:

                # 키워드가 사용자 질문 안에 들어있는지 확인
                if keyword in query:
                    # 핵심 키워드가 일치하면 중요도가 높으므로 2점을 부여
                    score += 2

            # 사용자 질문의 각 단어들이 FAQ의 질문 텍스트 자체에 포함되는지 확인
            for token in query_tokens:

                if len(token) > 1 and token in faq['question']:
                    # 질문의 단어가 FAQ 질문에 포함되어 있으면 1점 부여
                    score += 1

            # 만약 점수가 1점이라도 쌓였다면 (관련이 있다면) 결과 후보군에 추가
            if score > 0:
                results.append({"score": score, "faq": faq})

        # 모든 FAQ 검사가 끝나면, score가 높은 순서대로 내림차순(reverse=True) 정렬
        # x는 results의 각 요소이며, x["score"] 값을 기준으로 정렬하라는 뜻
        results.sort(key=lambda x: x["score"], reverse=True)
        
        # 정렬된 결과 중에서 상위 top_k개(기본 2개)만 골라내어, 점수를 제외한 순수 FAQ 데이터만 추출
        # [참고] Python의 슬라이싱([:top_k])을 사용해 리스트를 자름
        return [item["faq"] for item in results[:top_k]]
