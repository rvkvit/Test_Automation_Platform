
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app, url_for
import os

def send_invitation_email(email, token):
    """Send invitation email to user"""
    try:
        # For development, just log the invitation details
        invitation_url = url_for('auth.accept_invitation', token=token, _external=True)

        logging.info(f"Invitation sent to {email}")
        logging.info(f"Invitation URL: {invitation_url}")

        # In production, you would implement actual email sending here
        # using SMTP or a service like SendGrid, AWS SES, etc.

        print(f"=== INVITATION EMAIL ===")
        print(f"To: {email}")
        print(f"Subject: You're invited to join TestCraft Pro")
        print(f"Invitation Link: {invitation_url}")
        print(f"========================")

        return True

    except Exception as e:
        logging.error(f"Failed to send invitation email: {e}")
        raise

def send_password_reset_email(email, token):
    """Send password reset email"""
    try:
        reset_url = url_for('auth.reset_password', token=token, _external=True)

        logging.info(f"Password reset email sent to {email}")
        logging.info(f"Reset URL: {reset_url}")

        print(f"=== PASSWORD RESET EMAIL ===")
        print(f"To: {email}")
        print(f"Subject: Reset your TestCraft Pro password")
        print(f"Reset Link: {reset_url}")
        print(f"============================")

        return True

    except Exception as e:
        logging.error(f"Failed to send password reset email: {e}")
        raise

def configure_email(app):
    """Configure email settings"""
    # Email configuration would go here
    # For now, we'll use console logging for development
    logging.basicConfig(level=logging.INFO)

class EmailService:
    """Email service class for backward compatibility"""
    
    @staticmethod
    def send_invitation(email, token):
        return send_invitation_email(email, token)
    
    @staticmethod
    def send_password_reset(email, token):
        return send_password_reset_email(email, token)
