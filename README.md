# Automated Issue Detection & Escalation System

Intelligent monitoring system that detects issues in Elasticsearch logs and automatically escalates them through Slack, Email, and Jira.

## Key Features

- Real-time Elasticsearch log monitoring
- Pattern-based issue detection (ERROR, Exception, FATAL)
- Multi-channel alerts (Slack, Email, Jira)
- Severity-based escalation rules
- Comprehensive audit logging

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Add your credentials to .env:
   # - Elasticsearch API key
   # - Slack webhook URL and bot token
   # - Gmail account with App Password
   # - Jira API token
   ```

3. **Update Configuration**
   - Edit `config.yaml` for:
     - Alert thresholds
     - Notification channels
     - Escalation rules

4. **Run the System**
   ```bash
   python src/main.py
   ```

## Directory Structure
```
src/
├── monitors/          # Log monitoring
├── alerting/         # Alert handling
└── utils/            # Helper utilities
```

## Testing

Run test logs:
```bash
python test_logs.py
```

Verify environment:
```bash
python check_env.py
```

## License

MIT License 