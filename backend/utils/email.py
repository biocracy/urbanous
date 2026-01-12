
import os
import httpx
from pydantic import EmailStr

# We use HTTP API now because SMTP ports (587, 465, 2525) are blocked or timing out in Railway.
SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"

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
    Sends a verification email with the token link using SendGrid HTTP API (v3).
    """
    api_key = os.getenv("MAIL_PASSWORD") # We reuse this var for the API Key
    if not api_key:
        print(f"WARNING: No API Key (MAIL_PASSWORD). Verification Link: http://localhost:3000/verify?token={token}")
        return

    # Construct Link
    base_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    whitelist_url = f"{base_url}/verify?token={token}"
    
    sender_email = os.getenv("MAIL_FROM", "noreply@urbanous.net")

    payload = {
        "personalizations": [
            {
                "to": [{"email": email}],
                "subject": "Verify your OpenNews Account"
            }
        ],
        "from": {"email": sender_email, "name": "Urbanous Team"},
        "content": [
            {
                "type": "text/html",
                "value": html_template.format(link=whitelist_url)
            }
        ]
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(SENDGRID_API_URL, json=payload, headers=headers, timeout=10.0)
            if response.status_code >= 200 and response.status_code < 300:
                print(f"Email sent successfully to {email}")
            else:
                print(f"Failed to send email. Status: {response.status_code}")
                print(f"Response: {response.text}")
                # We can choose to raise an error if we want it logged as an exception
                raise Exception(f"SendGrid Error: {response.text}")
                
        except Exception as e:
            print(f"Exception sending email via HTTP: {e}")
            raise e
