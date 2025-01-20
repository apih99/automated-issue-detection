import os
from typing import Dict, Any, List
from loguru import logger
from .channels.slack import SlackNotifier
from .channels.email import EmailNotifier
from .channels.jira import JiraNotifier

class AlertManager:
    """
    Manages alert distribution across different channels based on severity and configuration.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the alert manager with configuration.
        
        Args:
            config: Full configuration dictionary
        """
        logger.info("Initializing Alert Manager")
        self.config = config
        self.notifiers = {}
        
        # Get alerting configuration
        alert_config = config.get('alerting', {})
        logger.debug(f"Alert configuration: {alert_config}")
        
        # Initialize Slack notifier
        if alert_config.get('slack', {}).get('enabled'):
            logger.info("Initializing Slack notifier...")
            try:
                webhook_url = os.getenv('SLACK_WEBHOOK_URL')
                bot_token = os.getenv('SLACK_BOT_TOKEN')
                logger.debug(f"Slack webhook URL found: {bool(webhook_url)}")
                logger.debug(f"Slack bot token found: {bool(bot_token)}")
                
                self.notifiers['slack'] = SlackNotifier(alert_config['slack'])
                logger.info("Slack notifier initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Slack notifier: {str(e)}")
        
        # Initialize Email notifier
        if alert_config.get('email', {}).get('enabled'):
            logger.info("Initializing Email notifier...")
            try:
                email_from = os.getenv('ALERT_EMAIL_FROM')
                email_password = os.getenv('EMAIL_PASSWORD')
                logger.debug(f"Email from address found: {bool(email_from)}")
                logger.debug(f"Email password found: {bool(email_password)}")
                
                self.notifiers['email'] = EmailNotifier(alert_config['email'])
                logger.info("Email notifier initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Email notifier: {str(e)}")
        
        # Initialize Jira notifier
        if alert_config.get('jira', {}).get('enabled'):
            logger.info("Initializing Jira notifier...")
            try:
                jira_server = os.getenv('JIRA_SERVER')
                jira_token = os.getenv('JIRA_API_TOKEN')
                jira_email = os.getenv('JIRA_USER_EMAIL')
                logger.debug(f"Jira server found: {bool(jira_server)}")
                logger.debug(f"Jira API token found: {bool(jira_token)}")
                logger.debug(f"Jira user email found: {bool(jira_email)}")
                
                self.notifiers['jira'] = JiraNotifier(alert_config['jira'])
                logger.info("Jira notifier initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Jira notifier: {str(e)}")
        
        logger.info(f"Initialized notifiers: {list(self.notifiers.keys())}")
        
        if not self.notifiers:
            logger.warning("No alert channels are enabled!")
            
        # Load escalation configuration
        self.escalation_config = config.get('escalation', {})
        logger.debug("Escalation configuration:")
        for severity in ['critical', 'high', 'warning']:
            if severity in self.escalation_config:
                channels = self.escalation_config[severity].get('channels', [])
                logger.debug(f"  {severity}: {channels}")
                
                # Verify channels exist
                for channel in channels:
                    if channel not in self.notifiers:
                        logger.warning(f"Channel '{channel}' specified in {severity} escalation but not configured")
    
    def send_alert(self, 
                  title: str,
                  message: str,
                  severity: str,
                  metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Send an alert through appropriate channels based on severity.
        
        Args:
            title: Alert title
            message: Alert message
            severity: Alert severity level
            metadata: Additional alert metadata
            
        Returns:
            List of dictionaries containing the status of each alert sent
        """
        if severity not in ['critical', 'high', 'warning']:
            logger.error(f"Invalid severity level: {severity}")
            return []
        
        results = []
        metadata = metadata or {}
        
        # Get channels for this severity level
        logger.debug(f"Processing alert - Title: {title}, Severity: {severity}")
        
        # Get channels from escalation config
        channels = self.escalation_config.get(severity, {}).get('channels', [])
        if not channels:
            logger.warning(f"No channels configured for severity level: {severity}")
            return []
            
        logger.debug(f"Configured channels for {severity}: {channels}")
        
        for channel in channels:
            if channel not in self.notifiers:
                logger.warning(f"Channel {channel} not configured but specified in escalation rules")
                continue
                
            try:
                logger.debug(f"Sending alert through channel: {channel}")
                notifier = self.notifiers[channel]
                result = notifier.send(title, message, severity, metadata)
                
                if result.get('status') == 'sent':
                    logger.info(f"Successfully sent {severity} alert through {channel}")
                    results.append({
                        'channel': channel,
                        'success': True,
                        'result': result
                    })
                else:
                    error_msg = result.get('error', 'Unknown error')
                    logger.error(f"Failed to send alert through {channel}: {error_msg}")
                    results.append({
                        'channel': channel,
                        'success': False,
                        'error': error_msg
                    })
            except Exception as e:
                error_msg = f"Error processing alert through {channel}: {str(e)}"
                logger.error(error_msg)
                results.append({
                    'channel': channel,
                    'success': False,
                    'error': error_msg
                })
        
        if not results:
            logger.warning(f"No alerts were sent for {severity} alert: {title}")
        
        return results
    
    def create_incident(self,
                       title: str,
                       description: str,
                       severity: str,
                       metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create an incident ticket in the configured system (e.g., Jira).
        
        Args:
            title: Incident title
            description: Incident description
            severity: Incident severity level
            metadata: Additional incident metadata
            
        Returns:
            Dictionary containing the incident creation status and details
        """
        if 'jira' not in self.notifiers:
            logger.error("Jira integration not configured for incident creation")
            return {'success': False, 'error': 'Jira not configured'}
        
        try:
            result = self.notifiers['jira'].create_incident(
                title,
                description,
                severity,
                metadata or {}
            )
            return {'success': True, 'result': result}
        except Exception as e:
            logger.error(f"Failed to create incident: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def update_incident(self,
                       incident_id: str,
                       status: str,
                       comment: str = None,
                       metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Update an existing incident ticket.
        
        Args:
            incident_id: ID of the incident to update
            status: New incident status
            comment: Optional comment to add
            metadata: Additional update metadata
            
        Returns:
            Dictionary containing the update status and details
        """
        if 'jira' not in self.notifiers:
            logger.error("Jira integration not configured for incident updates")
            return {'success': False, 'error': 'Jira not configured'}
        
        try:
            result = self.notifiers['jira'].update_incident(
                incident_id,
                status,
                comment,
                metadata or {}
            )
            return {'success': True, 'result': result}
        except Exception as e:
            logger.error(f"Failed to update incident {incident_id}: {str(e)}")
            return {'success': False, 'error': str(e)} 