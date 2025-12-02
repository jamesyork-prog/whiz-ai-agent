#!/bin/bash
# Start the webhook server in the Docker container

echo "Starting webhook server on port 8801..."
docker-compose exec -d parlant python /app/app_tools/webhook_server.py

sleep 2

echo "Checking if webhook server is running..."
if curl -s http://localhost:8801/health > /dev/null 2>&1; then
    echo "✅ Webhook server is running on http://localhost:8801"
else
    echo "⚠️  Webhook server may not be responding yet. Check logs:"
    echo "   docker-compose logs -f parlant"
fi

echo ""
echo "Webhook endpoint: http://localhost:8801/webhook/freshdesk"
echo "Webhook secret: -sWyn5y-WKNX8rgNgNReE-XRe9_-A44e9duRpWbt10s"
