import os
from datetime import datetime
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Elasticsearch client
es_config = {
    'hosts': ["https://my-elasticsearch-project-a47d61.es.us-east-1.aws.elastic.cloud:443"],
    'api_key': os.getenv('ES_API_KEY'),
    'ssl_assert_fingerprint': None,
}

try:
    # Connect to Elasticsearch
    es = Elasticsearch(**es_config)
    print("Successfully connected to Elasticsearch")

    # Test log entries with more varied scenarios
    test_logs = [
        {
            "message": "FATAL ERROR: System crash in production environment",
            "severity": "FATAL",
            "@timestamp": datetime.utcnow().isoformat(),
            "service": "payment-service",
            "environment": "production",
            "error_code": "FATAL-001",
            "impact": "Payment processing stopped"
        },
        {
            "message": "ERROR: Database connection timeout after 30 seconds",
            "severity": "ERROR",
            "@timestamp": datetime.utcnow().isoformat(),
            "service": "database-service",
            "environment": "production",
            "error_code": "DB-001",
            "impact": "Queries delayed"
        },
        {
            "message": "Exception caught: NullPointerException in UserAuthentication",
            "severity": "ERROR",
            "@timestamp": datetime.utcnow().isoformat(),
            "service": "auth-service",
            "environment": "production",
            "error_code": "AUTH-001",
            "stack_trace": "java.lang.NullPointerException at UserAuth.java:120"
        },
        {
            "message": "FATAL: Security breach detected - Multiple failed login attempts",
            "severity": "FATAL",
            "@timestamp": datetime.utcnow().isoformat(),
            "service": "security-service",
            "environment": "production",
            "error_code": "SEC-001",
            "impact": "Account locked",
            "location": "US-East"
        },
        {
            "message": "ERROR: API rate limit exceeded for customer service",
            "severity": "ERROR",
            "@timestamp": datetime.utcnow().isoformat(),
            "service": "api-gateway",
            "environment": "production",
            "error_code": "API-001",
            "client_id": "customer-service-1"
        }
    ]

    # Insert test logs
    for log in test_logs:
        response = es.index(
            index="search-oxl8",
            document=log
        )
        print(f"\nInserted log:")
        print(f"Message: {log['message']}")
        print(f"Severity: {log['severity']}")
        print(f"Service: {log['service']}")
        print(f"Response: {response['result']}")

    print("\nTest logs inserted successfully!")
    print("Wait a minute for the monitoring system to detect these logs.")

except Exception as e:
    print(f"Error: {str(e)}") 