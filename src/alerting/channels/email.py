import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List
from loguru import logger

class EmailNotifier:
    """
    Handles sending notifications via email.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the email notifier.
        
        Args:
            config: Email configuration dictionary
        """
        logger.debug(f"Initializing Email notifier with config: {config}")
        self.smtp_server = config['smtp_server']
        self.smtp_port = config['smtp_port']
        self.from_address = config['from_address']
        self.recipients = config['recipients']
        
        # Get email password from environment
        self.password = os.getenv('EMAIL_PASSWORD')
        if not self.password:
            logger.error("EMAIL_PASSWORD not found in environment variables")
            raise ValueError("EMAIL_PASSWORD not configured")
        
        # Test SMTP connection
        try:
            logger.debug(f"Testing SMTP connection to {self.smtp_server}:{self.smtp_port}")
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.from_address, self.password)
                logger.info("Successfully connected to SMTP server")
        except Exception as e:
            logger.error(f"Failed to connect to SMTP server: {str(e)}")
            raise
    
    def format_message(self,
                      title: str,
                      message: str,
                      severity: str,
                      metadata: Dict[str, Any]) -> str:
        """
        Format an HTML email message.
        
        Args:
            title: Alert title
            message: Alert message
            severity: Alert severity
            metadata: Additional metadata
            
        Returns:
            Formatted HTML message
        """
        severity_colors = {
            'critical': '#FF0000',
            'high': '#FFA500',
            'warning': '#FFFF00'
        }
        
        metadata_html = '<br>'.join([f"<strong>{k}:</strong> {v}" for k, v in metadata.items()])
        
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: {severity_colors.get(severity, '#808080')};">
                        🚨 {title}
                    </h2>
                    <div style="margin: 20px 0; padding: 15px; background-color: #f5f5f5; border-radius: 5px;">
                        <p>{message}</p>
                    </div>
                    <div style="margin: 20px 0;">
                        <p><strong>Severity:</strong> {severity.upper()}</p>
                        {metadata_html}
                    </div>
                    <hr>
                    <p style="color: #666; font-size: 12px;">
                        This is an automated alert from the Issue Detection System.
                    </p>
                </div>
            </body>
        </html>
        """
        return html
    
    def get_recipients(self, severity: str) -> List[str]:
        """
        Get the list of recipients for a given severity level.
        
        Args:
            severity: Alert severity level
            
        Returns:
            List of email addresses
        """
        return self.recipients.get(severity, [])
    
    def send(self,
            title: str,
            message: str,
            severity: str,
            metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Send an email alert.
        
        Args:
            title: Alert title
            message: Alert message
            severity: Alert severity
            metadata: Additional metadata
            
        Returns:
            Dictionary containing the email send status
        """
        logger.debug(f"Preparing to send email alert - Title: {title}, Severity: {severity}")
        
        # Get recipients for this severity
        recipients = self.recipients.get(severity, [])
        if not recipients:
            logger.warning(f"No recipients configured for severity level: {severity}")
            return {"status": "skipped", "reason": "no_recipients"}
        
        # Format email
        logger.debug("Formatting email message")
        html = self.format_message(title, message, severity, metadata or {})
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"[{severity.upper()}] {title}"
        msg['From'] = self.from_address
        msg['To'] = ', '.join(recipients)
        msg.attach(MIMEText(html, 'html'))
        
        try:
            logger.debug(f"Connecting to SMTP server {self.smtp_server}:{self.smtp_port}")
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                logger.debug("Logging into SMTP server")
                server.login(self.from_address, self.password)
                logger.debug(f"Sending email to {recipients}")
                server.send_message(msg)
                logger.info(f"Successfully sent email to {recipients}")
                return {"status": "sent", "recipients": recipients}
        except Exception as e:
            error_msg = f"Failed to send email: {str(e)}"
            logger.error(error_msg)
            return {"status": "failed", "error": error_msg} 