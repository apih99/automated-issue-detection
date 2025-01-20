import os
import yaml
from pathlib import Path
from loguru import logger

def load_config(config_path: str = "config/config.yaml") -> dict:
    """
    Load and validate the configuration file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        dict: Validated configuration dictionary
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_file, 'r') as f:
        try:
            config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML configuration: {str(e)}")
    
    validate_config(config)
    expand_env_vars(config)
    
    return config

def validate_config(config: dict) -> None:
    """
    Validate the configuration structure and required fields.
    
    Args:
        config: Configuration dictionary to validate
        
    Raises:
        ValueError: If configuration is invalid
    """
    required_sections = ['monitors', 'alerting', 'escalation', 'audit']
    
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required configuration section: {section}")
    
    # Validate monitors
    if not any(monitor['enabled'] for monitor in config['monitors'].values()):
        raise ValueError("At least one monitor must be enabled")
    
    # Validate alerting
    if not any(channel['enabled'] for channel in config['alerting'].values()):
        raise ValueError("At least one alerting channel must be enabled")
    
    # Validate escalation rules
    required_severities = ['critical', 'high', 'warning']
    for severity in required_severities:
        if severity not in config['escalation']:
            raise ValueError(f"Missing escalation rules for severity: {severity}")

def expand_env_vars(config: dict) -> None:
    """
    Recursively expand environment variables in configuration values.
    
    Args:
        config: Configuration dictionary to process
    """
    if isinstance(config, dict):
        for key, value in config.items():
            if isinstance(value, (dict, list)):
                expand_env_vars(value)
            elif isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                config[key] = os.getenv(env_var)
                if config[key] is None:
                    logger.warning(f"Environment variable not set: {env_var}")
    
    elif isinstance(config, list):
        for i, value in enumerate(config):
            if isinstance(value, (dict, list)):
                expand_env_vars(value)
            elif isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                config[i] = os.getenv(env_var)
                if config[i] is None:
                    logger.warning(f"Environment variable not set: {env_var}") 