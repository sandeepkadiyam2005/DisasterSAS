import os
import logging

logger = logging.getLogger(__name__)

try:
    from twilio.rest import Client
except Exception:  # pragma: no cover - handled gracefully at runtime
    Client = None


def _get_recipients():
    raw = os.environ.get("SMS_ALERT_RECIPIENTS", "")
    recipients = [item.strip() for item in raw.replace(";", ",").split(",") if item.strip()]
    return recipients


def send_sms_alert(city, alert, temperature, humidity, wind_speed):
    """
    Sends disaster alert SMS to recipients configured in SMS_ALERT_RECIPIENTS.

    Required env vars:
    - TWILIO_ACCOUNT_SID
    - TWILIO_AUTH_TOKEN
    - TWILIO_FROM_NUMBER
    - SMS_ALERT_RECIPIENTS (comma-separated phone numbers in E.164 format)
    """
    recipients = _get_recipients()
    if not recipients:
        logger.warning("SMS alerts skipped: SMS_ALERT_RECIPIENTS is empty")
        return {"sent": 0, "failed": 0}

    if Client is None:
        logger.error("SMS alerts skipped: twilio package not installed")
        return {"sent": 0, "failed": len(recipients)}

    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_number = os.environ.get("TWILIO_FROM_NUMBER")

    if not account_sid or not auth_token or not from_number:
        logger.warning(
            "SMS alerts skipped: missing TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_FROM_NUMBER"
        )
        return {"sent": 0, "failed": len(recipients)}

    body = (
        f"DisasterSAS Alert: {alert} in {city}. "
        f"Temp: {temperature}C, Humidity: {humidity}%, Wind: {wind_speed} m/s. "
        "Please take precautions."
    )

    client = Client(account_sid, auth_token)
    sent = 0
    failed = 0

    for to_number in recipients:
        try:
            client.messages.create(body=body, from_=from_number, to=to_number)
            sent += 1
        except Exception as exc:
            failed += 1
            logger.error("Failed to send SMS to %s: %s", to_number, str(exc))

    logger.info("SMS alert dispatch completed: sent=%s failed=%s", sent, failed)
    return {"sent": sent, "failed": failed}

