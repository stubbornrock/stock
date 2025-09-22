import os
import smtplib
from logger_utils import get_logger
from logging.handlers import TimedRotatingFileHandler
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr

load_dotenv()
# ========== 邮件配置 ==========
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = os.getenv("SMTP_PORT")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

# ========== 日志配置 =========
logger = get_logger("EBMMonitor")


def send_email(receiver_emails, info, title, content):
    """
    Sends an email to a list of recipients.
    """
    if not all([SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD]):
        logger.error("SMTP configuration missing, cannot send email.")
        return False

    message = MIMEText(content, 'plain', 'utf-8')
    #message['From'] = Header("华北2-910B库存提醒", 'utf-8')
    #message['To'] = Header(", ".join(receiver_emails), 'utf-8')
    message['From'] = formataddr((str(Header(f"{info}库存提醒", 'utf-8')), SENDER_EMAIL))
    message['To'] = ", ".join(receiver_emails)
    message['Subject'] = Header(title, 'utf-8')

    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, int(SMTP_PORT))
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, receiver_emails, message.as_string())
        server.quit()
        logger.info(f"✅ Email '{title}' sent successfully to {receiver_emails}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send email '{title}'. Error: {e}")
        return False


if __name__ == "__main__":
    logger.info("Running mail.py in test mode...")
    test_recipients = ["chengs4@chinatelecom.cn"]
    test_title = "Test Email from mail.py"
    test_content = "This is a test email sent from the mail.py script."

    if send_email(test_recipients, test_title, test_content):
        logger.info("Test email function executed successfully.")
    else:
        logger.error("Test email function failed. Check log for details.")
