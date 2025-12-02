#!/usr/bin/env python3
"""
Generate Freshdesk Webhook Configuration

This script generates:
1. A secure webhook secret
2. Configuration documentation
3. Environment variable updates
"""

import secrets
import os
from pathlib import Path


def generate_webhook_secret(length: int = 32) -> str:
    """Generate a cryptographically secure webhook secret."""
    return secrets.token_urlsafe(length)


def get_webhook_url() -> str:
    """Get the webhook URL based on environment or prompt user."""
    # Check if we have a public URL configured
    public_url = os.getenv("PUBLIC_WEBHOOK_URL")
    
    if public_url:
        return f"{public_url}/webhook/freshdesk"
    
    # Default for local development
    return "http://localhost:8000/webhook/freshdesk"


def generate_config():
    """Generate complete webhook configuration."""
    
    webhook_secret = generate_webhook_secret()
    webhook_url = get_webhook_url()
    
    config = {
        "webhook_url": webhook_url,
        "webhook_secret": webhook_secret,
        "request_type": "POST",
        "encoding": "JSON",
        "content_type": "Advanced"
    }
    
    return config


def print_configuration(config: dict):
    """Print configuration in a readable format."""
    
    print("=" * 70)
    print("FRESHDESK WEBHOOK CONFIGURATION")
    print("=" * 70)
    print()
    
    print("📋 FRESHDESK SETTINGS")
    print("-" * 70)
    print(f"Request Type:     {config['request_type']}")
    print(f"URL:              {config['webhook_url']}")
    print(f"Encoding:         {config['encoding']}")
    print(f"Content Type:     {config['content_type']}")
    print()
    
    print("🔐 WEBHOOK SECRET (Save this securely!)")
    print("-" * 70)
    print(f"{config['webhook_secret']}")
    print()
    
    print("📝 EVENTS TO SUBSCRIBE")
    print("-" * 70)
    print("✓ Ticket is created")
    print("✓ Ticket is updated")
    print("✓ Note is added")
    print("✓ Ticket priority is changed")
    print("✓ Ticket status is changed")
    print()
    
    print("🔧 ENVIRONMENT VARIABLE")
    print("-" * 70)
    print("Add this to your .env file:")
    print()
    print(f"FRESHDESK_WEBHOOK_SECRET={config['webhook_secret']}")
    print()
    
    print("🌐 CUSTOM HEADERS (Optional)")
    print("-" * 70)
    print("If Freshdesk supports custom headers, add:")
    print(f"X-Webhook-Secret: {config['webhook_secret']}")
    print()
    
    print("=" * 70)
    print()


def save_to_file(config: dict):
    """Save configuration to a file."""
    
    output_file = Path("scripts/webhook_config_output.txt")
    
    with open(output_file, "w") as f:
        f.write("=" * 70 + "\n")
        f.write("FRESHDESK WEBHOOK CONFIGURATION\n")
        f.write("=" * 70 + "\n\n")
        
        f.write("FRESHDESK SETTINGS\n")
        f.write("-" * 70 + "\n")
        f.write(f"Request Type:     {config['request_type']}\n")
        f.write(f"URL:              {config['webhook_url']}\n")
        f.write(f"Encoding:         {config['encoding']}\n")
        f.write(f"Content Type:     {config['content_type']}\n\n")
        
        f.write("WEBHOOK SECRET\n")
        f.write("-" * 70 + "\n")
        f.write(f"{config['webhook_secret']}\n\n")
        
        f.write("EVENTS TO SUBSCRIBE\n")
        f.write("-" * 70 + "\n")
        f.write("- Ticket is created\n")
        f.write("- Ticket is updated\n")
        f.write("- Note is added\n")
        f.write("- Ticket priority is changed\n")
        f.write("- Ticket status is changed\n\n")
        
        f.write("ENVIRONMENT VARIABLE\n")
        f.write("-" * 70 + "\n")
        f.write(f"FRESHDESK_WEBHOOK_SECRET={config['webhook_secret']}\n\n")
        
        f.write("CUSTOM HEADERS (Optional)\n")
        f.write("-" * 70 + "\n")
        f.write(f"X-Webhook-Secret: {config['webhook_secret']}\n\n")
    
    print(f"✅ Configuration saved to: {output_file}")
    print()


def main():
    """Main execution."""
    
    print()
    print("🚀 Generating Freshdesk Webhook Configuration...")
    print()
    
    # Check for existing secret
    existing_secret = os.getenv("FRESHDESK_WEBHOOK_SECRET")
    if existing_secret:
        print("⚠️  WARNING: FRESHDESK_WEBHOOK_SECRET already exists in environment")
        print(f"   Current value: {existing_secret[:10]}...")
        print()
        response = input("Generate a new secret? (y/N): ").strip().lower()
        if response != 'y':
            print("Keeping existing secret.")
            config = generate_config()
            config['webhook_secret'] = existing_secret
            print_configuration(config)
            save_to_file(config)
            return
    
    # Generate new configuration
    config = generate_config()
    
    # Display configuration
    print_configuration(config)
    
    # Save to file
    save_to_file(config)
    
    print("📚 NEXT STEPS:")
    print("-" * 70)
    print("1. Copy the FRESHDESK_WEBHOOK_SECRET to your .env file")
    print("2. Restart your Docker containers: docker-compose up -d --force-recreate")
    print("3. Ensure your webhook URL is publicly accessible")
    print("4. Configure the webhook in Freshdesk Admin → Automations → Webhooks")
    print("5. Test the webhook using Freshdesk's test feature")
    print()


if __name__ == "__main__":
    main()
