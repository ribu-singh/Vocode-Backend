#!/bin/bash
# Update script for Vocode WebSocket Server
# This script pulls the latest code, installs dependencies, and restarts the service

set -e  # Exit on error

echo "🔄 Updating Vocode WebSocket Server..."

# Navigate to project root
cd ~/vocode-core || { echo "❌ Error: ~/vocode-core directory not found"; exit 1; }

# Pull latest code
echo "📥 Pulling latest code from repository..."
git pull origin main || {
    echo "⚠️  Warning: git pull failed. Continuing anyway..."
}

# Navigate to client_backend directory
cd apps/client_backend || { echo "❌ Error: apps/client_backend directory not found"; exit 1; }

# Install dependencies
echo "📦 Installing dependencies..."
poetry install || {
    echo "❌ Error: poetry install failed"
    exit 1
}

# Restart the service
echo "🔄 Restarting vocode-websocket.service..."
sudo systemctl restart vocode-websocket.service || {
    echo "❌ Error: Failed to restart service"
    exit 1
}

# Wait a moment for service to start
sleep 2

# Check service status
echo "✅ Checking service status..."
if sudo systemctl is-active --quiet vocode-websocket.service; then
    echo "✅ Service is running successfully!"
    echo ""
    echo "📋 Service status:"
    sudo systemctl status vocode-websocket.service --no-pager -l || true
else
    echo "❌ Service failed to start. Check logs with:"
    echo "   sudo journalctl -u vocode-websocket.service -n 50 --no-pager"
    exit 1
fi

echo ""
echo "✨ Update complete!"
echo "📝 View logs with: sudo journalctl -u vocode-websocket.service -f"

