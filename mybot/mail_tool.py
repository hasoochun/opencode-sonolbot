import imaplib
import smtplib
import email
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import time
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

NAVER_ID = os.getenv('NAVER_ID')
NAVER_PW = os.getenv('NAVER_PASSWORD')

class NaverMailClient:
    def __init__(self):
        self.imap_server = os.getenv('NAVER_IMAP_SERVER', "imap.naver.com")
        self.smtp_server = os.getenv('NAVER_SMTP_SERVER', "smtp.naver.com")
        self.user = NAVER_ID if NAVER_ID else ""
        self.password = NAVER_PW if NAVER_PW else ""

    def connect_imap(self):
        try:
            imap = imaplib.IMAP4_SSL(self.imap_server)
            imap.login(self.user, self.password)
            return imap
        except Exception as e:
            print(f"[ERROR] IMAP Connection Failed: {e}")
            return None

    def connect_smtp(self):
        try:
            smtp = smtplib.SMTP_SSL(self.smtp_server, 465)
            smtp.login(self.user, self.password)
            return smtp
        except Exception as e:
            print(f"[ERROR] SMTP Connection Failed: {e}")
            return None

    def get_subject(self, msg):
        subject, encoding = decode_header(msg["Subject"])[0]
        if isinstance(subject, bytes):
            if encoding is None or encoding.lower() == 'unknown-8bit':
                try:
                    subject = subject.decode('utf-8')
                except:
                    subject = subject.decode('latin-1', errors='replace')
            else:
                try:
                    subject = subject.decode(encoding)
                except LookupError: # Fallback for other unknown encodings
                    subject = subject.decode('utf-8', errors='replace')
        return subject

    def get_body(self, msg):
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                if "attachment" not in content_disposition:
                    try:
                        body = part.get_payload(decode=True).decode()
                        return body
                    except:
                        pass
        else:
            return msg.get_payload(decode=True).decode()
        return ""

    def send_email(self, to_email, subject, body, attachment_path=None):
        smtp = self.connect_smtp()
        if not smtp:
            return False

        msg = MIMEMultipart()
        msg["From"] = f"{self.user}@naver.com"
        msg["To"] = to_email
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain"))

        if attachment_path and os.path.exists(attachment_path):
            from email.mime.base import MIMEBase
            from email import encoders
            
            filename = os.path.basename(attachment_path)
            with open(attachment_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename= {filename}",
            )
            msg.attach(part)

        try:
            smtp.sendmail(f"{self.user}@naver.com", to_email, msg.as_string())
            smtp.quit()
            return True
        except Exception as e:
            print(f"[ERROR] Send Mail Failed: {e}")
            return False
