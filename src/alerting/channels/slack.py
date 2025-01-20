import os
from typing import Dict, Any
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from loguru import logger

class SlackNotifier:
    """
    Handles sending notifications to Slack channels.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Slack notifier.
        
        Args:
            config: Slack configuration dictionary
        """
        logger.debug(f"Initializing Slack notifier with config: {config}")
        self.webhook_url = config['webhook_url']
        self.default_channel = config['default_channel']
        self.mention_users = config['mention_users']
        
        # Initialize Slack client
        slack_token = os.getenv('SLACK_BOT_TOKEN')
        if not slack_token:
            logger.error("SLACK_BOT_TOKEN not found in environment variables")
            raise ValueError("SLACK_BOT_TOKEN not configured")
            
        logger.debug("Initializing Slack client...")
        self.client = WebClient(token=slack_token)
        
        # Test connection
        try:
            response = self.client.auth_test()
            logger.info(f"Successfully connected to Slack as {response['user']}")
        except SlackApiError as e:
            logger.error(f"Failed to connect to Slack: {str(e)}")
            raise
    
    def format_message(self,
                      title: str,
                      message: str,
                      severity: str,
                      metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format a message for Slack with proper styling and mentions.
        
        Args:
            title: Alert title
            message: Alert message
            severity: Alert severity
            metadata: Additional metadata
            
        Returns:
            Formatted Slack message payload
        """
        # Determine color based on severity
        colors = {
            'critical': '#FF0000',  # Red
            'high': '#FFA500',      # Orange
            'warning': '#FFFF00'    # Yellow
        }
        
        # Get users to mention
        mentions = ' '.join(self.mention_users.get(severity, []))
        
        # Format metadata
        metadata_text = '\n'.join([f"*{k}:* {v}" for k, v in metadata.items()])
        
        # Create fallback text
        fallback = f"{title}\n{message}\nSeverity: {severity.upper()}"
        if metadata:
            fallback += f"\nMetadata: {metadata}"
        
        return {
            "text": fallback,  # Top-level fallback text
            "attachments": [
                {
                    "fallback": fallback,  # Attachment-level fallback
                    "color": colors.get(severity, '#808080'),
                    "blocks": [
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": f"🚨 {title}"
                            }
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"{mentions}\n{message}"
                            }
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*Severity:* {severity.upper()}\n{metadata_text}"
                            }
                        },
                        {
                            "type": "context",
                            "elements": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"Sent by Automated Issue Detection System"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    
    def send(self,
             title: str,
             message: str,
             severity: str,
             metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Send a message to Slack.
        
        Args:
            title: Alert title
            message: Alert message
            severity: Alert severity
            metadata: Additional metadata
            
        Returns:
            Dictionary containing the send status and details
        """
        logger.debug(f"Preparing to send Slack message - Title: {title}, Severity: {severity}")
            
        try:
            # Format message
            logger.debug("Formatting Slack message")
            payload = self.format_message(title, message, severity, metadata or {})
            
            # Send to Slack
            logger.debug(f"Sending message to channel: {self.default_channel}")
            response = self.client.chat_postMessage(
                channel=self.default_channel,
                **payload
            )
            
            if response['ok']:
                logger.info(f"Successfully sent message to Slack channel {self.default_channel}")
                return {
                    'status': 'sent',
                    'channel': self.default_channel,
                    'ts': response['ts']
                }
            else:
                error_msg = f"Slack API returned not ok: {response.get('error', 'Unknown error')}"
                logger.error(error_msg)
                return {
                    'status': 'failed',
                    'error': error_msg
                }
            
        except SlackApiError as e:
            error_msg = f"Failed to send Slack message: {str(e)}"
            logger.error(error_msg)
            return {
                'status': 'failed',
                'error': error_msg
            }
    
    def update_message(self,
                      message_id: str,
                      title: str,
                      message: str,
                      severity: str,
                      metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Update an existing Slack message.
        
        Args:
            message_id: Slack message timestamp ID
            title: New alert title
            message: New alert message
            severity: New alert severity
            metadata: New metadata
            
        Returns:
            Dictionary containing the Slack API response
        """
        try:
            payload = self.format_message(title, message, severity, metadata or {})
            
            response = self.client.chat_update(
                channel=self.default_channel,
                ts=message_id,
                text=f"{title} - {message}",  # Fallback text
                **payload
            )
            
            if not response['ok']:
                raise SlackApiError(f"Failed to update message: {response['error']}", response)
            
            logger.info(f"Successfully updated Slack alert: {title}")
            return {'message_id': response['ts'], 'channel': response['channel']}
            
        except SlackApiError as e:
            logger.error(f"Error updating Slack alert: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating Slack alert: {str(e)}")
            raise 