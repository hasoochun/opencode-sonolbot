import argparse
import json
import os
import email
import sys
from mail_tool import NaverMailClient

# 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KEYWORD = "소놀봇"
MEMORY_DIR = os.path.join(BASE_DIR, "memory")
WORKSPACE_DIR = os.path.join(BASE_DIR, "workspace")
PROCESSED_LOG = os.path.join(BASE_DIR, "processed_mails.json")
INPUT_FILE = os.path.join(MEMORY_DIR, "task_instruction.txt")
OUTPUT_FILE = os.path.join(MEMORY_DIR, "result.txt")
META_FILE = os.path.join(MEMORY_DIR, "current_meta.json") # 보낸 사람 정보 등 임시 저장

# Ensure memory directory exists
os.makedirs(MEMORY_DIR, exist_ok=True)

def load_processed_ids():
    if not os.path.exists(PROCESSED_LOG):
        return []
    with open(PROCESSED_LOG, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return []

def save_processed_id(msg_id):
    ids = load_processed_ids()
    if msg_id not in ids:
        ids.append(msg_id)
        with open(PROCESSED_LOG, "w", encoding="utf-8") as f:
            json.dump(ids, f, indent=4)

def save_meta(sender, subject):
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump({"sender": sender, "subject": subject}, f)

def load_meta():
    if not os.path.exists(META_FILE):
        return None, None
    with open(META_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("sender"), data.get("subject")

def check_mail():
    client = NaverMailClient()
    imap = client.connect_imap()
    if not imap:
        return

    imap.select("INBOX")
    # 날짜 기준 검색 추가 (오늘 날짜)
    import datetime
    date_str = datetime.date.today().strftime("%d-%b-%Y")
    
    # UNSEEN(안 읽은 메일) + SINCE(오늘 이후) 검색
    # 예: (UNSEEN SINCE "30-Jan-2025")
    search_criteria = f'(UNSEEN SINCE "{date_str}")'
    status, messages = imap.search(None, search_criteria)
    
    if status != "OK":
        print("No messages found or error.")
        return

    msg_ids = messages[0].split()
    processed_ids = load_processed_ids()
    
    task_found = False

    # 최신 메일부터 확인
    for num in reversed(msg_ids):
        # 1. 헤더만 먼저 가져와서 제목 확인 (속도 최적화)
        res, msg_data = imap.fetch(num, "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM MESSAGE-ID)])")
        
        header_content = b""
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                header_content += response_part[1]
        
        if not header_content:
            continue

        msg = email.message_from_bytes(header_content)
        subject = client.get_subject(msg)
        msg_id_header = msg.get("Message-ID", "").strip()
        
        # 키워드 확인 (소놀봇)
        if KEYWORD in subject:
            print(f"Target Mail Found: {subject}")
            
            # 2. 타겟 메일이면 전체 본문 다운로드
            res, full_msg_data = imap.fetch(num, "(RFC822)")
            for response_part in full_msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    sender = msg.get("From")
                    # Sender parsing (Name <email@addr.com>)
                    sender_email = ""
                    if sender:
                        if "<" in sender:
                            try:
                                sender_email = sender.split("<")[1].strip(">")
                            except:
                                sender_email = sender
                        else:
                            sender_email = sender.strip()
                    else:
                        print("Unknown Sender")
                        continue

                    body = client.get_body(msg)
                    
                    # 작업 파일 저장
                    with open(INPUT_FILE, "w", encoding="utf-8") as f:
                        f.write(f"Subject: {subject}\n\nTask:\n{body}")
                    
                    # 메타 정보 저장 (답장용)
                    save_meta(sender_email, subject)
                    
                    # 처리 완료 기록
                    save_processed_id(msg_id_header)
                    task_found = True
                    break # 한 번에 하나씩 처리 (권장)
        
        if task_found:
            break

    imap.close()
    imap.logout()

    if task_found:
        print("TASK_READY")
    else:
        print("NO_TASK")

def reply_mail(result_text=None):
    if not os.path.exists(META_FILE):
        print("No meta file found. Cannot reply.")
        return

    sender, subject = load_meta()
    if not sender:
        print("No sender info.")
        return

    # 결과 파일 읽기 (인자가 없으면 기본 파일에서)
    content = ""
    if result_text:
        content = result_text
    elif os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = "작업이 완료되었으나 결과 내용이 없습니다."

    # 제목에 [Re] 붙이기
    reply_subject = f"Re: {subject}"
    if "[처리완료]" not in reply_subject:
        reply_subject = f"[처리완료] {reply_subject}"

    client = NaverMailClient()
    success = client.send_email(sender, reply_subject, content)
    
    if success:
        print(f"Reply sent to {sender}")
        # 메타 파일 삭제 (작업 끝)
        os.remove(META_FILE)
        if os.path.exists(INPUT_FILE):
            os.remove(INPUT_FILE)
        if os.path.exists(OUTPUT_FILE):
            os.remove(OUTPUT_FILE)
    else:
        print("Failed to send reply.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Check for new mails")
    parser.add_argument("--reply", action="store_true", help="Send reply email")
    args = parser.parse_args()

    if args.check:
        check_mail()
    elif args.reply:
        reply_mail()
    else:
        print("Use --check or --reply")

if __name__ == "__main__":
    main()
