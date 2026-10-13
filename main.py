import os
import smtplib
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

# 1. 정보 수집 (구글 뉴스 RSS 예시)
def get_latest_news():
    url = "https://news.google.com/rss/search?q=인공지능&hl=ko&gl=KR&ceid=KR:ko"
    feed = feedparser.parse(url)
    
    collected = []
    for entry in feed.entries[:3]:
        collected.append(f"- 제목: {entry.title}\n  링크: {entry.link}")
    
    return "\n".join(collected), len(feed.entries[:3])

# 2. 작업 완료 알림 메일 발송 함수
def send_completion_email(item_count):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    subject = f"[알림] 제미나이 자동 정보 수집 및 요약이 완료되었습니다 ({now_str})"
    body = f"""안녕하세요!

설정해 두신 스케줄에 따라 제미나이의 정보 수집 및 요약 작업이 정상적으로 완료되었습니다.

- 실행 시각: {now_str}
- 처리된 항목: 총 {item_count}건
- 모델 처리 상태: 성공 (Completed)

상세 결과는 저장소의 실행 로그 및 지정된 저장소에서 확인하실 수 있습니다.
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
        print("완료 알림 메일 발송 성공!")
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
    
    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt
    )
    
    # 요약 결과는 서버 콘솔/로그에 정상 기록
    print("=== [요약 완료 내용] ===")
    print(response.text)
    
    print("[3/3] 완료 알림 메일 전송 중...")
    send_completion_email(item_count)

if __name__ == "__main__":
    main()
