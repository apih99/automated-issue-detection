import os
from typing import Dict, Any, List
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
from loguru import logger

class ElasticsearchMonitor:
    """
    Monitors Elasticsearch logs for patterns indicating issues.
    """
    
    def __init__(self, config: Dict[str, Any], alert_manager: Any, audit_logger: Any):
        """
        Initialize the Elasticsearch monitor.
        
        Args:
            config: Elasticsearch configuration dictionary
            alert_manager: AlertManager instance for sending alerts
            audit_logger: AuditLogger instance for logging events
        """
        self.hosts = config['hosts']
        self.indices = config['indices']
        self.patterns = config['patterns']
        self.interval = config['search_interval']
        self.alert_manager = alert_manager
        self.audit_logger = audit_logger
        
        # Initialize Elasticsearch client with API key authentication
        es_config = {
            'hosts': self.hosts,
            'api_key': os.getenv('ES_API_KEY'),
            'ssl_assert_fingerprint': None,  # Disable certificate verification for development
            'request_timeout': 30,  # 30 second timeout
        }
        
        try:
            self.client = Elasticsearch(**es_config)
            
            # Verify connection
            if not self.client.ping():
                raise ConnectionError("Could not connect to Elasticsearch")
            logger.info("Successfully connected to Elasticsearch")
            
            # List available indices
            indices = self.client.indices.get_alias(index="*")
            logger.info(f"Available Elasticsearch indices: {', '.join(indices.keys())}")
            
            # Check if our configured indices exist
            for index_pattern in self.indices:
                matching_indices = self.client.indices.get(index=index_pattern, ignore_unavailable=True)
                if not matching_indices:
                    logger.warning(f"No indices found matching pattern: {index_pattern}")
                else:
                    logger.info(f"Found {len(matching_indices)} indices matching pattern: {index_pattern}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Elasticsearch: {str(e)}")
            raise ConnectionError(f"Could not connect to Elasticsearch: {str(e)}")
    
    def build_query(self, pattern: str, time_from: datetime) -> Dict[str, Any]:
        """
        Build Elasticsearch query for log pattern.
        
        Args:
            pattern: Pattern to search for
            time_from: Start time for the search
            
        Returns:
            Elasticsearch query dictionary
        """
        return {
            "query": {
                "bool": {
                    "must": [
                        {
                            "query_string": {
                                "query": pattern,
                                "analyze_wildcard": True
                            }
                        },
                        {
                            "range": {
                                "@timestamp": {
                                    "gte": time_from.isoformat(),
                                    "lte": "now"
                                }
                            }
                        }
                    ]
                }
            },
            "sort": [
                {"@timestamp": {"order": "desc"}}
            ],
            "size": 100  # Limit results
        }
    
    def search_logs(self,
                   pattern: str,
                   severity: str,
                   time_from: datetime) -> List[Dict[str, Any]]:
        """
        Search for log patterns in Elasticsearch.
        
        Args:
            pattern: Pattern to search for
            severity: Severity level of the pattern
            time_from: Start time for the search
            
        Returns:
            List of matching log entries
        """
        try:
            query = self.build_query(pattern, time_from)
            logger.debug(f"Searching for pattern '{pattern}' from {time_from}")
            
            # Search across all configured indices
            results = []
            for index in self.indices:
                logger.debug(f"Searching in index: {index}")
                try:
                    response = self.client.search(
                        index=index,
                        body=query
                    )
                    
                    hits = response['hits']['hits']
                    logger.debug(f"Found {len(hits)} hits in index {index}")
                    
                    if hits:
                        results.extend([
                            {
                                'index': index,
                                'timestamp': hit['_source'].get('@timestamp'),
                                'message': hit['_source'].get('message'),
                                'severity': severity,
                                'pattern': pattern,
                                'metadata': {
                                    k: v for k, v in hit['_source'].items()
                                    if k not in ['@timestamp', 'message']
                                }
                            }
                            for hit in hits
                        ])
                except Exception as e:
                    logger.error(f"Error searching index {index}: {str(e)}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching logs for pattern {pattern}: {str(e)}")
            self.audit_logger.log_error(
                "elasticsearch_monitor",
                f"Log search failed for pattern: {pattern}",
                {'error': str(e)}
            )
            return []
    
    def process_matches(self, matches: List[Dict[str, Any]]) -> None:
        """
        Process and alert on matching log entries.
        """
        # Group matches by pattern and severity
        grouped_matches = {}
        for match in matches:
            key = (match['pattern'], match['severity'])
            if key not in grouped_matches:
                grouped_matches[key] = []
            grouped_matches[key].append(match)
        
        # Send alerts for each group
        for (pattern, severity), pattern_matches in grouped_matches.items():
            count = len(pattern_matches)
            
            # Create alert message
            title = f"Log Pattern Detected: {pattern}"
            message = f"Found {count} matching log entries in the last interval.\n\n"
            message += "Sample messages:\n"
            
            # Add up to 5 sample messages
            for match in pattern_matches[:5]:
                message += f"- {match['timestamp']}: {match['message']}\n"
            
            # Send alert
            logger.info(f"Sending alert for pattern '{pattern}' with severity '{severity}'")
            alert_results = self.alert_manager.send_alert(
                title=title,
                message=message,
                severity=severity.lower(),  # Convert to lowercase to match expected values
                metadata={
                    'pattern': pattern,
                    'match_count': count,
                    'indices': list(set(m['index'] for m in pattern_matches)),
                    'time_range': f"Last {self.interval} seconds"
                }
            )
            
            # Log alert results
            for result in alert_results:
                if result['success']:
                    logger.info(f"Successfully sent alert through {result['channel']}")
                    if 'result' in result:
                        logger.debug(f"Alert details for {result['channel']}: {result['result']}")
                else:
                    logger.error(f"Failed to send alert through {result['channel']}: {result.get('error', 'Unknown error')}")
    
    def check(self) -> None:
        """
        Perform log pattern checks and send alerts if needed.
        """
        try:
            logger.debug("Starting Elasticsearch check...")
            time_from = datetime.utcnow() - timedelta(seconds=self.interval)
            all_matches = []
            
            # Search for each pattern
            for pattern_config in self.patterns:
                pattern = pattern_config['pattern']
                severity = pattern_config['severity']
                
                logger.debug(f"Checking pattern: {pattern} (severity: {severity})")
                matches = self.search_logs(pattern, severity, time_from)
                if matches:
                    logger.info(f"Found {len(matches)} matches for pattern: {pattern}")
                    all_matches.extend(matches)
            
            # Process matches if any found
            if all_matches:
                logger.info(f"Processing {len(all_matches)} total matches...")
                self.process_matches(all_matches)
            else:
                logger.debug("No matches found in this check interval")
            
            # Log check results
            self.audit_logger.log_monitor_check(
                "elasticsearch",
                {
                    'patterns_checked': len(self.patterns),
                    'matches_found': len(all_matches)
                },
                bool(all_matches)
            )
            
        except Exception as e:
            logger.error(f"Error in Elasticsearch monitor check: {str(e)}")
            self.audit_logger.log_error(
                "elasticsearch_monitor",
                "Check operation failed",
                {'error': str(e)}
            ) 