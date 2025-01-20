#!/usr/bin/env python3
import os
import sys
import time
import yaml
import schedule
from dotenv import load_dotenv
from loguru import logger
from pathlib import Path

# Add src directory to Python path
sys.path.append(str(Path(__file__).parent))

# Import local modules
from monitors.prometheus_monitor import PrometheusMonitor
from monitors.elasticsearch_monitor import ElasticsearchMonitor
from alerting.alert_manager import AlertManager
from utils.config_loader import load_config
from utils.audit_logger import AuditLogger

def setup_logging():
    """Configure logging settings."""
    log_path = Path("logs/app.log")
    log_path.parent.mkdir(exist_ok=True)
    
    logger.remove()  # Remove default handler
    
    # Set debug level for console output
    logger.add(
        sys.stdout,
        level="DEBUG",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <white>{message}</white>"
    )
    
    # Set info level for file output
    logger.add(
        log_path,
        level="INFO",
        rotation="1 day",
        retention="30 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )

def initialize_components(config):
    """Initialize monitoring and alerting components."""
    # Create alert manager with full config
    logger.info("Initializing Alert Manager...")
    alert_manager = AlertManager(config)
    
    # Create audit logger
    logger.info("Initializing Audit Logger...")
    audit_logger = AuditLogger(config["audit"])
    
    monitors = []
    
    # Initialize enabled monitors
    if config["monitors"]["prometheus"]["enabled"]:
        logger.info("Initializing Prometheus monitor...")
        prom_monitor = PrometheusMonitor(
            config["monitors"]["prometheus"],
            alert_manager,
            audit_logger
        )
        monitors.append(prom_monitor)
    
    if config["monitors"]["elasticsearch"]["enabled"]:
        logger.info("Initializing Elasticsearch monitor...")
        es_monitor = ElasticsearchMonitor(
            config["monitors"]["elasticsearch"],
            alert_manager,
            audit_logger
        )
        monitors.append(es_monitor)
    
    return monitors, alert_manager, audit_logger

def run_initial_checks(monitors):
    """Run initial checks for all monitors."""
    logger.info("Running initial checks...")
    for monitor in monitors:
        try:
            logger.info(f"Running initial check for {monitor.__class__.__name__}")
            monitor.check()
        except Exception as e:
            logger.error(f"Error in initial check for {monitor.__class__.__name__}: {str(e)}")

def schedule_monitoring(monitors):
    """Schedule monitoring tasks."""
    for monitor in monitors:
        logger.info(f"Scheduling monitor with interval: {monitor.interval} seconds")
        schedule.every(monitor.interval).seconds.do(monitor.check)

def main():
    """Main application entry point."""
    try:
        # Load environment variables
        load_dotenv()
        
        # Setup logging
        setup_logging()
        logger.info("Starting Automated Issue Detection & Escalation System")
        
        # Load configuration
        config = load_config()
        
        # Initialize components
        monitors, alert_manager, audit_logger = initialize_components(config)
        
        # Run initial checks
        run_initial_checks(monitors)
        
        # Schedule monitoring tasks
        schedule_monitoring(monitors)
        
        # Main loop
        logger.info("Entering main monitoring loop...")
        last_run_time = time.time()
        
        while True:
            current_time = time.time()
            schedule.run_pending()
            
            # Log status every minute
            if current_time - last_run_time >= 60:
                logger.info("Monitoring system is active...")
                last_run_time = current_time
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 