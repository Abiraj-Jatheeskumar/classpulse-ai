import os
import smtplib
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta


class EmailService:
    def __init__(self):
        self.smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        self.smtp_user = os.environ.get("SMTP_USER", "")
        self.smtp_password = os.environ.get("SMTP_PASSWORD", "")
        self.from_email = os.environ.get("FROM_EMAIL", self.smtp_user)
        self.frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")
        self.email_enabled = bool(self.smtp_user and self.smtp_password)

        if self.email_enabled:
            print(f"✅ SMTP email service initialized ({self.smtp_user})")
        else:
            print("⚠️ SMTP_USER or SMTP_PASSWORD not set — emails will be logged only")

    def generate_verification_token(self) -> str:
        return secrets.token_urlsafe(32)

    def get_token_expiry(self, hours: int = 24) -> datetime:
        return datetime.utcnow() + timedelta(hours=hours)

    def send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        if not self.email_enabled:
            print(f"⚠️ Email not configured. Would send to: {to_email} | Subject: {subject}")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = to_email
            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, to_email, msg.as_string())

            print(f"✅ Email sent to: {to_email}")
            return True

        except Exception as e:
            print(f"❌ Failed to send email to {to_email}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def send_verification_email(self, to_email: str, first_name: str, token: str) -> bool:
        verification_link = f"{self.frontend_url}/activate/{token}"
        year = datetime.now().year

        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify Your Email - Class Pulse</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f8fafc; -webkit-font-smoothing: antialiased;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f8fafc;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width: 520px;">
                    <tr>
                        <td align="center" style="padding-bottom: 32px;">
                            <table role="presentation" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td style="background: linear-gradient(135deg, #059669 0%, #0d9488 100%); padding: 12px 24px; border-radius: 50px;">
                                        <span style="color: #ffffff; font-size: 20px; font-weight: 700; letter-spacing: -0.5px;">Class Pulse</span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td style="background: #ffffff; border-radius: 16px; box-shadow: 0 4px 24px rgba(0,0,0,0.08); overflow: hidden;">
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                <tr><td style="height: 4px; background: linear-gradient(90deg, #059669 0%, #0d9488 50%, #06b6d4 100%);"></td></tr>
                            </table>
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td style="padding: 48px 40px;">
                                        <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                            <tr>
                                                <td align="center" style="padding-bottom: 24px;">
                                                    <div style="width:64px;height:64px;background:linear-gradient(135deg,#ecfdf5 0%,#d1fae5 100%);border-radius:50%;display:inline-block;line-height:64px;text-align:center;">
                                                        <span style="font-size:28px;">✉️</span>
                                                    </div>
                                                </td>
                                            </tr>
                                        </table>
                                        <h1 style="margin:0 0 8px 0;font-size:24px;font-weight:700;color:#111827;text-align:center;">Verify your email address</h1>
                                        <p style="margin:0 0 32px 0;font-size:15px;color:#6b7280;text-align:center;line-height:1.5;">
                                            Hi {first_name}, thanks for signing up! Please confirm your email to get started.
                                        </p>
                                        <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                            <tr>
                                                <td align="center" style="padding-bottom: 32px;">
                                                    <a href="{verification_link}"
                                                       style="display:inline-block;background:linear-gradient(135deg,#059669 0%,#0d9488 100%);color:#ffffff;padding:16px 40px;text-decoration:none;border-radius:8px;font-weight:600;font-size:15px;">
                                                        Verify Email Address
                                                    </a>
                                                </td>
                                            </tr>
                                        </table>
                                        <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                            <tr>
                                                <td style="border-top:1px solid #e5e7eb;padding-top:24px;">
                                                    <p style="margin:0 0 12px 0;font-size:13px;color:#9ca3af;text-align:center;">Or copy and paste this link:</p>
                                                    <p style="margin:0;font-size:13px;color:#059669;text-align:center;word-break:break-all;background:#f0fdf4;padding:12px 16px;border-radius:8px;border:1px solid #d1fae5;">
                                                        {verification_link}
                                                    </p>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 32px 20px; text-align: center;">
                            <p style="margin:0 0 8px 0;font-size:13px;color:#9ca3af;">This link expires in 24 hours.</p>
                            <p style="margin:0 0 16px 0;font-size:13px;color:#9ca3af;">If you didn't create an account, ignore this email.</p>
                            <p style="margin:0;font-size:12px;color:#d1d5db;">© {year} Class Pulse. All rights reserved.</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
        """
        return self.send_email(to_email, "Verify your email - Class Pulse", html_content)

    def send_password_reset_email(self, to_email: str, first_name: str, token: str) -> bool:
        reset_link = f"{self.frontend_url}/reset-password/{token}"
        year = datetime.now().year

        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reset Your Password - Class Pulse</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f8fafc;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f8fafc;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width: 520px;">
                    <tr>
                        <td align="center" style="padding-bottom: 32px;">
                            <table role="presentation" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td style="background: linear-gradient(135deg, #059669 0%, #0d9488 100%); padding: 12px 24px; border-radius: 50px;">
                                        <span style="color: #ffffff; font-size: 20px; font-weight: 700; letter-spacing: -0.5px;">Class Pulse</span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td style="background: #ffffff; border-radius: 16px; box-shadow: 0 4px 24px rgba(0,0,0,0.08); overflow: hidden;">
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                <tr><td style="height: 4px; background: linear-gradient(90deg, #059669 0%, #0d9488 50%, #06b6d4 100%);"></td></tr>
                            </table>
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td style="padding: 48px 40px;">
                                        <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                            <tr>
                                                <td align="center" style="padding-bottom: 24px;">
                                                    <div style="width:64px;height:64px;background:linear-gradient(135deg,#fef3c7 0%,#fde68a 100%);border-radius:50%;display:inline-block;line-height:64px;text-align:center;">
                                                        <span style="font-size:28px;">🔐</span>
                                                    </div>
                                                </td>
                                            </tr>
                                        </table>
                                        <h1 style="margin:0 0 8px 0;font-size:24px;font-weight:700;color:#111827;text-align:center;">Reset your password</h1>
                                        <p style="margin:0 0 32px 0;font-size:15px;color:#6b7280;text-align:center;line-height:1.5;">
                                            Hi {first_name}, we received a request to reset your password.
                                        </p>
                                        <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                            <tr>
                                                <td align="center" style="padding-bottom: 32px;">
                                                    <a href="{reset_link}"
                                                       style="display:inline-block;background:linear-gradient(135deg,#059669 0%,#0d9488 100%);color:#ffffff;padding:16px 40px;text-decoration:none;border-radius:8px;font-weight:600;font-size:15px;">
                                                        Reset Password
                                                    </a>
                                                </td>
                                            </tr>
                                        </table>
                                        <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                            <tr>
                                                <td style="border-top:1px solid #e5e7eb;padding-top:24px;">
                                                    <p style="margin:0 0 12px 0;font-size:13px;color:#9ca3af;text-align:center;">Or copy and paste this link:</p>
                                                    <p style="margin:0;font-size:13px;color:#059669;text-align:center;word-break:break-all;background:#f0fdf4;padding:12px 16px;border-radius:8px;border:1px solid #d1fae5;">
                                                        {reset_link}
                                                    </p>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 32px 20px; text-align: center;">
                            <p style="margin:0 0 8px 0;font-size:13px;color:#9ca3af;">This link expires in 1 hour.</p>
                            <p style="margin:0 0 16px 0;font-size:13px;color:#9ca3af;">If you didn't request this, ignore this email.</p>
                            <p style="margin:0;font-size:12px;color:#d1d5db;">© {year} Class Pulse. All rights reserved.</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
        """
        return self.send_email(to_email, "Reset your password - Class Pulse", html_content)

    def send_session_report_email(
        self,
        to_email: str,
        student_name: str,
        session_title: str,
        course_name: str,
        session_id: str,
        is_instructor: bool = False
    ) -> bool:
        report_link = f"{self.frontend_url}/dashboard/sessions/{session_id}/report"
        year = datetime.now().year

        intro_text = (
            f"The session <strong>{session_title}</strong> has ended. "
            f"Your session report is now available with detailed analytics."
        ) if is_instructor else (
            f"Thank you for attending <strong>{session_title}</strong>! "
            f"Your personal session report is now available."
        )

        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Session Report Available - Class Pulse</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f8fafc;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f8fafc;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width: 520px;">
                    <tr>
                        <td align="center" style="padding-bottom: 32px;">
                            <table role="presentation" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td style="background: linear-gradient(135deg, #059669 0%, #0d9488 100%); padding: 12px 24px; border-radius: 50px;">
                                        <span style="color: #ffffff; font-size: 20px; font-weight: 700; letter-spacing: -0.5px;">Class Pulse</span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td style="background: #ffffff; border-radius: 16px; box-shadow: 0 4px 24px rgba(0,0,0,0.08); overflow: hidden;">
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                <tr><td style="height: 4px; background: linear-gradient(90deg, #059669 0%, #0d9488 50%, #06b6d4 100%);"></td></tr>
                            </table>
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td style="padding: 48px 40px;">
                                        <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                            <tr>
                                                <td align="center" style="padding-bottom: 24px;">
                                                    <div style="width:64px;height:64px;background:linear-gradient(135deg,#ecfdf5 0%,#d1fae5 100%);border-radius:50%;display:inline-block;line-height:64px;text-align:center;">
                                                        <span style="font-size:28px;">📊</span>
                                                    </div>
                                                </td>
                                            </tr>
                                        </table>
                                        <h1 style="margin:0 0 8px 0;font-size:24px;font-weight:700;color:#111827;text-align:center;">Session Report Available</h1>
                                        <p style="margin:0 0 24px 0;font-size:15px;color:#6b7280;text-align:center;line-height:1.5;">
                                            Hi {student_name}, {intro_text}
                                        </p>
                                        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom:24px;background:#f9fafb;border-radius:8px;">
                                            <tr>
                                                <td style="padding: 16px;">
                                                    <p style="margin:0 0 8px 0;font-size:12px;color:#9ca3af;text-transform:uppercase;letter-spacing:0.5px;">Session</p>
                                                    <p style="margin:0 0 12px 0;font-size:16px;color:#111827;font-weight:600;">{session_title}</p>
                                                    <p style="margin:0;font-size:14px;color:#6b7280;">{course_name}</p>
                                                </td>
                                            </tr>
                                        </table>
                                        <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                            <tr>
                                                <td align="center" style="padding-bottom: 24px;">
                                                    <a href="{report_link}"
                                                       style="display:inline-block;background:linear-gradient(135deg,#059669 0%,#0d9488 100%);color:#ffffff;padding:16px 40px;text-decoration:none;border-radius:8px;font-weight:600;font-size:15px;">
                                                        View Report
                                                    </a>
                                                </td>
                                            </tr>
                                        </table>
                                        <p style="margin:0;font-size:13px;color:#9ca3af;text-align:center;">You can also download the report as a PDF from the report page.</p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 32px 20px; text-align: center;">
                            <p style="margin:0 0 16px 0;font-size:13px;color:#9ca3af;">This report contains your personalized learning analytics.</p>
                            <p style="margin:0;font-size:12px;color:#d1d5db;">© {year} Class Pulse. All rights reserved.</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
        """
        return self.send_email(to_email, f"Session Report: {session_title} - Class Pulse", html_content)


# Singleton instance
email_service = EmailService()
