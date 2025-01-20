import os
from dotenv import load_dotenv

def check_env_var(var_name, required=True):
    value = os.getenv(var_name)
    if value:
        print(f"✓ {var_name}: Found")
        if var_name.endswith('_TOKEN') or var_name.endswith('_KEY') or var_name.endswith('_PASSWORD'):
            print(f"  Length: {len(value)} characters")
        else:
            print(f"  Value: {value}")
    else:
        status = "MISSING (Required)" if required else "MISSING (Optional)"
        print(f"✗ {var_name}: {status}")
    return bool(value)

def main():
    print("Loading environment variables...")
    load_dotenv()
    print("\nChecking environment variables for alert channels:\n")
    
    # Slack Configuration
    print("Slack Configuration:")
    slack_vars = {
        'SLACK_WEBHOOK_URL': True,
        'SLACK_BOT_TOKEN': True
    }
    slack_ok = all(check_env_var(var, required) for var, required in slack_vars.items())
    
    print("\nEmail Configuration:")
    email_vars = {
        'ALERT_EMAIL_FROM': True,
        'EMAIL_PASSWORD': True
    }
    email_ok = all(check_env_var(var, required) for var, required in email_vars.items())
    
    print("\nJira Configuration:")
    jira_vars = {
        'JIRA_SERVER': True,
        'JIRA_API_TOKEN': True,
        'JIRA_USER_EMAIL': True
    }
    jira_ok = all(check_env_var(var, required) for var, required in jira_vars.items())
    
    print("\nSummary:")
    print(f"Slack Configuration: {'✓ Complete' if slack_ok else '✗ Incomplete'}")
    print(f"Email Configuration: {'✓ Complete' if email_ok else '✗ Incomplete'}")
    print(f"Jira Configuration: {'✓ Complete' if jira_ok else '✗ Incomplete'}")
    
    if not (slack_ok and email_ok and jira_ok):
        print("\nAction Required:")
        print("Please add the missing environment variables to your .env file")

if __name__ == "__main__":
    main() 