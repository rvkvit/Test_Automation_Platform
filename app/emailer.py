import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
from app.config import Config

logger = logging.getLogger(__name__)

class EmailService:
    
    @staticmethod
    def send_invitation_email(invitation_token, invited_by_user):
        """Send invitation email to a new user"""
        try:
            if not Config.SMTP_HOST or not Config.EMAIL_SENDER:
                logger.warning("Email configuration not set up, skipping invitation email")
                return {'success': False, 'error': 'Email not configured'}
            
            # Create email content
            subject = f"Invitation to join Test Automation Platform"
            
            # Generate invitation link (would be actual domain in production)
            base_url = "http://localhost:5000"  # This would come from config in production
            invitation_link = f"{base_url}/auth/accept-invite?token={invitation_token.token}"
            
            # Email body
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #007bff;">You're Invited!</h2>
                    
                    <p>Hello,</p>
                    
                    <p><strong>{invited_by_user.username}</strong> has invited you to join their Test Automation Platform team.</p>
                    
                    {f'<p><strong>Project:</strong> {invitation_token.project.name}</p>' if invitation_token.project else ''}
                    <p><strong>Role:</strong> {invitation_token.role.name}</p>
                    
                    <div style="margin: 30px 0;">
                        <a href="{invitation_link}" 
                           style="background-color: #007bff; color: white; padding: 12px 24px; 
                                  text-decoration: none; border-radius: 5px; display: inline-block;">
                            Accept Invitation
                        </a>
                    </div>
                    
                    <p style="color: #666; font-size: 14px;">
                        This invitation will expire on {invitation_token.expires_at.strftime('%B %d, %Y at %I:%M %p UTC')}.
                    </p>
                    
                    <p style="color: #666; font-size: 14px;">
                        If you can't click the button above, copy and paste this link into your browser:<br>
                        <code style="background-color: #f4f4f4; padding: 4px;">{invitation_link}</code>
                    </p>
                    
                    <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                    
                    <p style="color: #666; font-size: 12px;">
                        This is an automated message. Please do not reply to this email.
                    </p>
                </div>
            </body>
            </html>
            """
            
            text_content = f"""
            You're Invited!
            
            {invited_by_user.username} has invited you to join their Test Automation Platform team.
            
            {'Project: ' + invitation_token.project.name if invitation_token.project else ''}
            Role: {invitation_token.role.name}
            
            Please click the following link to accept your invitation:
            {invitation_link}
            
            This invitation will expire on {invitation_token.expires_at.strftime('%B %d, %Y at %I:%M %p UTC')}.
            
            This is an automated message. Please do not reply to this email.
            """
            
            # Send the email
            result = EmailService._send_email(
                to_email=invitation_token.email,
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to send invitation email: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def send_execution_summary_email(execution_result, recipient_email):
        """Send test execution summary email"""
        try:
            if not Config.SMTP_HOST or not Config.EMAIL_SENDER:
                logger.warning("Email configuration not set up, skipping summary email")
                return {'success': False, 'error': 'Email not configured'}
            
            # Determine email content based on execution result
            status_emoji = "✅" if execution_result.status.value == "passed" else "❌"
            status_color = "#28a745" if execution_result.status.value == "passed" else "#dc3545"
            
            script_name = execution_result.test_script.name if execution_result.test_script else "Suite Run"
            project_name = execution_result.project.name
            
            subject = f"{status_emoji} Test Execution: {script_name} - {execution_result.status.value.title()}"
            
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="background-color: {status_color}; color: white; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                        <h2 style="margin: 0;">{status_emoji} Test Execution Complete</h2>
                    </div>
                    
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                        <h3 style="margin-top: 0;">Execution Summary</h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 8px 0; font-weight: bold;">Project:</td>
                                <td style="padding: 8px 0;">{project_name}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; font-weight: bold;">Script:</td>
                                <td style="padding: 8px 0;">{script_name}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; font-weight: bold;">Status:</td>
                                <td style="padding: 8px 0; color: {status_color}; font-weight: bold;">
                                    {execution_result.status.value.title()}
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; font-weight: bold;">Duration:</td>
                                <td style="padding: 8px 0;">{execution_result.duration_seconds:.2f} seconds</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; font-weight: bold;">Started:</td>
                                <td style="padding: 8px 0;">{execution_result.started_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</td>
                            </tr>
                        </table>
                    </div>
                    
                    {f'''
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                        <h3 style="margin-top: 0;">Test Results</h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 8px 0; font-weight: bold;">Total Tests:</td>
                                <td style="padding: 8px 0;">{execution_result.tests_total}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; font-weight: bold;">Passed:</td>
                                <td style="padding: 8px 0; color: #28a745;">{execution_result.tests_passed}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; font-weight: bold;">Failed:</td>
                                <td style="padding: 8px 0; color: #dc3545;">{execution_result.tests_failed}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; font-weight: bold;">Pass Rate:</td>
                                <td style="padding: 8px 0;">{execution_result.pass_rate:.1f}%</td>
                            </tr>
                        </table>
                    </div>
                    ''' if execution_result.tests_total > 0 else ''}
                    
                    {f'<div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin-bottom: 20px;"><h4 style="margin-top: 0; color: #856404;">Error Details</h4><p style="margin-bottom: 0; color: #856404;">{execution_result.error_message}</p></div>' if execution_result.error_message else ''}
                    
                    <p style="color: #666; font-size: 14px;">
                        Executed by: <strong>{execution_result.executed_by.username}</strong><br>
                        Execution Mode: {'Headless' if execution_result.headless else 'Headed'}
                    </p>
                    
                    <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                    
                    <p style="color: #666; font-size: 12px;">
                        This is an automated message from your Test Automation Platform.
                    </p>
                </div>
            </body>
            </html>
            """
            
            # Send the email
            result = EmailService._send_email(
                to_email=recipient_email,
                subject=subject,
                html_content=html_content
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to send execution summary email: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def _send_email(to_email, subject, html_content, text_content=None):
        """Send an email using SMTP"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = Config.EMAIL_SENDER
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add text content if provided
            if text_content:
                msg.attach(MIMEText(text_content, 'plain'))
            
            # Add HTML content
            msg.attach(MIMEText(html_content, 'html'))
            
            # Connect to SMTP server and send
            with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT) as server:
                if Config.SMTP_USE_TLS:
                    server.starttls()
                
                if Config.SMTP_USER and Config.SMTP_PASS:
                    server.login(Config.SMTP_USER, Config.SMTP_PASS)
                
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def test_email_configuration():
        """Test email configuration by sending a test email"""
        try:
            if not Config.SMTP_HOST or not Config.EMAIL_SENDER:
                return {'success': False, 'error': 'Email configuration incomplete'}
            
            # Test SMTP connection
            with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT) as server:
                if Config.SMTP_USE_TLS:
                    server.starttls()
                
                if Config.SMTP_USER and Config.SMTP_PASS:
                    server.login(Config.SMTP_USER, Config.SMTP_PASS)
            
            return {'success': True, 'message': 'Email configuration is valid'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
