import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


def send_email_alert(city, alert, temperature, humidity, wind_speed):
    sender_email = os.environ.get("ALERT_SENDER_EMAIL", "sandeepkadiyam0@gmail.com")
    sender_password = os.environ.get("ALERT_SENDER_PASSWORD", "oxpw zcpv sktm ymzl")
    receiver_email = os.environ.get("ALERT_RECEIVER_EMAIL", "sandeepkadiyam0@gmail.com")

    subject = f"⚠ Disaster Alert in {city}"

    body = f"""
Disaster Alert Detected!
========================

City: {city}
Alert: {alert}

Temperature: {temperature}°C
Humidity: {humidity}%
Wind Speed: {wind_speed} m/s

Please take necessary precautions immediately.
"""

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        logger.info(f"Alert email sent for {city}")
    except Exception as e:
        logger.error(f"Failed to send alert email: {str(e)}")