import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from loguru import logger

class AuditLogger:
    """
    Handles audit logging for all monitoring and alerting activities.
    Provides a traceable history of events for compliance and debugging.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the audit logger.
        
        Args:
            config: Audit configuration dictionary
        """
        self.enabled = config.get('enabled', True)
        self.log_file = Path(config.get('log_file', 'logs/audit.log'))
        self.retention_days = config.get('retention_days', 90)
        
        # Ensure log directory exists
        self.log_file.parent.mkdir(exist_ok=True)
        
        if self.enabled:
            logger.info(f"Audit logging enabled. Writing to {self.log_file}")
    
    def log_event(self, event_type: str, details: Dict[str, Any], severity: str = "info") -> None:
        """
        Log an audit event.
        
        Args:
            event_type: Type of event (e.g., 'monitor_check', 'alert_sent')
            details: Dictionary containing event details
            severity: Event severity level
        """
        if not self.enabled:
            return
        
        timestamp = datetime.utcnow().isoformat()
        
        event = {
            "timestamp": timestamp,
            "event_type": event_type,
            "severity": severity,
            "details": details
        }
        
        try:
            with open(self.log_file, 'a') as f:
                json.dump(event, f)
                f.write('\n')
        except Exception as e:
            logger.error(f"Failed to write audit log: {str(e)}")
    
    def log_monitor_check(self, monitor_name: str, metrics: Dict[str, Any], issues_found: bool) -> None:
        """
        Log a monitoring check event.
        
        Args:
            monitor_name: Name of the monitor
            metrics: Dictionary of metrics checked
            issues_found: Whether any issues were detected
        """
        self.log_event(
            "monitor_check",
            {
                "monitor": monitor_name,
                "metrics": metrics,
                "issues_found": issues_found
            }
        )
    
    def log_alert_sent(self, alert_type: str, channel: str, recipient: str, message: str) -> None:
        """
        Log an alert being sent.
        
        Args:
            alert_type: Type of alert (e.g., 'slack', 'email')
            channel: Channel the alert was sent to
            recipient: Alert recipient
            message: Alert message
        """
        self.log_event(
            "alert_sent",
            {
                "alert_type": alert_type,
                "channel": channel,
                "recipient": recipient,
                "message": message
            },
            severity="warning"
        )
    
    def log_error(self, component: str, error_message: str, details: Dict[str, Any]) -> None:
        """
        Log an error event.
        
        Args:
            component: Component where the error occurred
            error_message: Error message
            details: Additional error details
        """
        self.log_event(
            "error",
            {
                "component": component,
                "error_message": error_message,
                "details": details
            },
            severity="error"
        )
    
    def log_system_event(self, event_name: str, details: Dict[str, Any]) -> None:
        """
        Log a system event.
        
        Args:
            event_name: Name of the system event
            details: Event details
        """
        self.log_event(
            "system_event",
            {
                "event_name": event_name,
                "details": details
            }
        ) 