#!/bin/bash
# Startup script to launch both Parlant and Webhook servers

set -e

echo "=========================================="
echo "Starting Parlant Services"
echo "=========================================="

# Start the webhook server in the background
echo "Starting webhook server on port 8801..."
python /app/app_tools/webhook_server.py &
WEBHOOK_PID=$!

# Give webhook server a moment to start
sleep 2

# Check if webhook server started successfully
if ps -p $WEBHOOK_PID > /dev/null; then
    echo "✅ Webhook server started (PID: $WEBHOOK_PID)"
else
    echo "⚠️  Webhook server failed to start"
fi

# Start the main Parlant server (this will run in foreground)
echo "Starting Parlant server on port 8800..."
echo "=========================================="
python main.py

# If main.py exits, kill the webhook server
kill $WEBHOOK_PID 2>/dev/null || true
