import os
import smtplib
import time
import urllib.parse
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import feedparser
from google import genai

# 환경 변수 불러오기
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")       # 발신용 지메일 주소
APP_PASSWORD = os.getenv("APP_PASSWORD")       # 구글 16자리 앱 비밀번호
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")   # 알림을 받을 지메일 주소

client = genai.Client(api_key=GEMINI_API_KEY)

# 1. 정보 수집 (복수 키워드 순회 수집)
def get_latest_news():
    keywords = [
        "인터랙션 디자인",
        "촉각 인터페이스",
        "하드웨어 UX",
        "디지털 디톡스"
    ]
    
    collected = []
    seen_links = set()  # 중복 기사 방지

    for kw in keywords:
        encoded_kw = urllib.parse.quote(kw)
        url = f"https://news.google.com/rss/search?q={encoded_kw}&hl=ko&gl=KR&ceid=KR:ko"
        feed = feedparser.parse(url)
        
        # 키워드당 최신 2건씩 추출
        for entry in feed.entries[:2]:
            if entry.link not in seen_links:
                seen_links.add(entry.link)
                collected.append(f"[{kw}] 제목: {entry.title}\n링크: {entry.link}")
    
    return "\n\n".join(collected), len(collected)

# 2. 요약 내용 포함 메일 발송 함수
def send_completion_email(item_count, summary_text):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    subject = f"[알림] 제미나이 일일 정보 수집 및 요약 리포트 ({now_str})"
    body = f"""안녕하세요!

설정해 두신 스케줄에 따라 제미나이의 정보 수집 및 요약 작업이 완료되었습니다.

- 실행 시각: {now_str}
- 수집 항목: 총 {item_count}건
- 모델 처리 상태: 성공 (Completed)

==================================================
[제미나이 요약 내용]
==================================================

{summary_text}

==================================================
상세 로그는 저장소의 실행 기록에서도 확인하실 수 있습니다.
"""

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("요약 결과 메일 발송 성공!")
    except Exception as e:
        print(f"메일 발송 실패: {e}")

def main():
    print("[1/3] 정보 수집 중...")
    news_text, item_count = get_latest_news()
    
    print("[2/3] 제미나이 모델 요약 실행 중...")
    prompt = f"""
    다음 수집된 뉴스를 읽고 핵심을 요약해줘:
    {news_text}
    """
    
    # 503 일시적 서버 과부하 대응: 최대 3회 자동 재시도
    response = None
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt
            )
            break
        except Exception as e:
            if attempt < 2:
                print(f"서버 일시 지연(503) 감지. 5초 후 다시 시도합니다... ({attempt + 1}/3)")
                time.sleep(5)
            else:
                raise e
    
    # 요약 결과 콘솔 출력
    print("=== [요약 완료 내용] ===")
    print(response.text)
    
    print("[3/3] 요약 내용 포함 메일 전송 중...")
    send_completion_email(item_count, response.text)

if __name__ == "__main__":
    main()
