import os
from typing import Dict, Any, List
import requests
from datetime import datetime, timedelta
from loguru import logger

class PrometheusMonitor:
    """
    Monitors Prometheus metrics for anomalies and threshold violations.
    """
    
    def __init__(self, config: Dict[str, Any], alert_manager: Any, audit_logger: Any):
        """
        Initialize the Prometheus monitor.
        
        Args:
            config: Prometheus configuration dictionary
            alert_manager: AlertManager instance for sending alerts
            audit_logger: AuditLogger instance for logging events
        """
        self.endpoint = config['endpoint']
        self.metrics = config['metrics']
        self.interval = config['scrape_interval']
        self.alert_manager = alert_manager
        self.audit_logger = audit_logger
        
        # Authentication
        self.auth = None
        if os.getenv('PROM_USERNAME') and os.getenv('PROM_PASSWORD'):
            self.auth = (os.getenv('PROM_USERNAME'), os.getenv('PROM_PASSWORD'))
    
    def query_metric(self, metric_name: str, duration: str = "5m") -> Dict[str, Any]:
        """
        Query a metric from Prometheus.
        
        Args:
            metric_name: Name of the metric to query
            duration: Time duration for the query
            
        Returns:
            Dictionary containing the query result
            
        Raises:
            Exception: If the query fails
        """
        try:
            # Build query URL
            query_url = f"{self.endpoint}/api/v1/query"
            
            # Create PromQL query
            query = f"{metric_name}[{duration}]"
            
            # Make request
            response = requests.get(
                query_url,
                params={'query': query},
                auth=self.auth,
                timeout=10
            )
            
            if response.status_code != 200:
                raise Exception(f"Query failed with status {response.status_code}: {response.text}")
            
            data = response.json()
            if data['status'] != 'success':
                raise Exception(f"Query returned error status: {data['status']}")
            
            return data['data']
            
        except Exception as e:
            logger.error(f"Failed to query metric {metric_name}: {str(e)}")
            raise
    
    def check_threshold(self,
                       metric_name: str,
                       threshold: float,
                       values: List[float]) -> Dict[str, Any]:
        """
        Check if metric values exceed the threshold.
        
        Args:
            metric_name: Name of the metric
            threshold: Threshold value
            values: List of metric values
            
        Returns:
            Dictionary containing violation details if any
        """
        violations = []
        max_value = max(values) if values else 0
        
        if max_value > threshold:
            violations.append({
                'metric': metric_name,
                'threshold': threshold,
                'value': max_value,
                'timestamp': datetime.utcnow().isoformat()
            })
        
        return violations
    
    def check(self) -> None:
        """
        Perform metric checks and send alerts if needed.
        """
        try:
            all_violations = []
            
            for metric in self.metrics:
                metric_name = metric['name']
                threshold = metric['threshold']
                severity = metric['severity']
                
                try:
                    # Query metric
                    result = self.query_metric(metric_name)
                    
                    # Extract values
                    values = []
                    for series in result.get('result', []):
                        values.extend([float(v[1]) for v in series.get('values', [])])
                    
                    # Check threshold
                    violations = self.check_threshold(metric_name, threshold, values)
                    
                    if violations:
                        all_violations.extend(violations)
                        
                        # Send alert for each violation
                        for violation in violations:
                            self.alert_manager.send_alert(
                                title=f"Metric Threshold Violation: {metric_name}",
                                message=f"Metric {metric_name} exceeded threshold of {threshold}. Current value: {violation['value']}",
                                severity=severity,
                                metadata={
                                    'metric': metric_name,
                                    'threshold': threshold,
                                    'current_value': violation['value'],
                                    'timestamp': violation['timestamp']
                                }
                            )
                
                except Exception as e:
                    logger.error(f"Error checking metric {metric_name}: {str(e)}")
                    self.audit_logger.log_error(
                        "prometheus_monitor",
                        f"Failed to check metric {metric_name}",
                        {'error': str(e)}
                    )
            
            # Log check results
            self.audit_logger.log_monitor_check(
                "prometheus",
                {
                    'metrics_checked': len(self.metrics),
                    'violations_found': len(all_violations)
                },
                bool(all_violations)
            )
            
        except Exception as e:
            logger.error(f"Error in Prometheus monitor check: {str(e)}")
            self.audit_logger.log_error(
                "prometheus_monitor",
                "Check operation failed",
                {'error': str(e)}
            ) 