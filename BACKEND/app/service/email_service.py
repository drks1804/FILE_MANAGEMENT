import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"


def send_email(to_email: str, subject: str, body: str):
    message = EmailMessage()

    message["From"] = SMTP_USERNAME
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    message.set_content("Please use an HTML-compatible email client to view this message.")

    message.add_alternative(body, subtype="html")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
        server.ehlo()

        if SMTP_USE_TLS:
            server.starttls()
            server.ehlo()

        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(message)
