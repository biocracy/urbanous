
import os
from typing import List
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
from pathlib import Path

# Load env variables (ensuring these are set in Railway)
conf = ConnectionConfig(
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", ""),
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", ""),
    MAIL_FROM = os.getenv("MAIL_FROM", "noreply@urbanous.net"),
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587)),
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_STARTTLS = False if int(os.getenv("MAIL_PORT", 587)) == 465 else True,
    MAIL_SSL_TLS = True if int(os.getenv("MAIL_PORT", 587)) == 465 else False,
    USE_CREDENTIALS = True,
    VALIDATE_CERTS = True
)


html_template = """
<!DOCTYPE html>
<html>
<head>
</head>
<body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; background-color: #f9f9f9; padding: 20px; border-radius: 8px;">
        <h2 style="color: #2563eb;">Welcome to OpenNews (Urbanous)</h2>
        <p>Please verify your email address to activate your account.</p>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{link}" style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold;">Verify Email</a>
        </p>
        <p>Or copy this link:</p>
        <p style="word-break: break-all; color: #666; font-size: 12px;">{link}</p>
    </div>
</body>
</html>
"""

async def send_verification_email(email: EmailStr, token: str):
    """
    Sends a verification email with the token link.
    """
    # Allow local dev verification if no SMTP configured
    if not os.getenv("MAIL_USERNAME"):
        print(f"WARNING: SMTP not configured. Verification Link: http://localhost:3000/verify?token={token}")
        return

    # Construct Link (Use FRONTEND_URL if available, else localhost default)
    base_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    whitelist_url = f"{base_url}/verify?token={token}"

    message = MessageSchema(
        subject="Verify your OpenNews Account",
        recipients=[email],
        body=html_template.format(link=whitelist_url),
        subtype=MessageType.html
    )

    fm = FastMail(conf)
    try:
        await fm.send_message(message)
        print(f"Email sent to {email}")
    except Exception as e:
        print(f"Failed to send email: {e}")
        raise e
