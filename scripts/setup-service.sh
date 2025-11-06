#!/bin/bash

# Setup systemd service for Vocode on GCP
# Run this script on the GCP instance after deployment

set -e

USERNAME=$(whoami)
WORK_DIR="$HOME/vocode-core/quickstarts"
ENV_FILE="/etc/vocode/.env"
SERVICE_FILE="/etc/systemd/system/vocode.service"

echo "🔧 Setting up Vocode systemd service..."

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "⚠️  Creating environment file template at $ENV_FILE"
    sudo mkdir -p /etc/vocode
    sudo tee "$ENV_FILE" > /dev/null <<EOF
OPENAI_API_KEY=your_openai_key_here
ELEVENLABS_API_KEY=your_elevenlabs_key_here
DEEPGRAM_API_KEY=your_deepgram_key_here
PULSE_SERVER=unix:/tmp/pulse-socket
EOF
    echo "📝 Please edit $ENV_FILE and add your API keys:"
    echo "   sudo nano $ENV_FILE"
    echo ""
    read -p "Press Enter after you've updated the .env file..."
fi

# Create systemd service file
echo "📝 Creating systemd service file..."
sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Vocode Streaming Application
After=network.target

[Service]
Type=simple
User=$USERNAME
WorkingDirectory=$WORK_DIR
Environment="PATH=$HOME/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
EnvironmentFile=$ENV_FILE
ExecStart=$HOME/.local/bin/poetry run python stream5.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Set permissions
sudo chmod 600 "$ENV_FILE"
sudo chown $USERNAME:$USERNAME "$ENV_FILE"

# Configure PulseAudio for headless operation
echo "🔊 Configuring PulseAudio..."
sudo sed -i '/^load-module module-null-sink/d' /etc/pulse/default.pa
echo "load-module module-null-sink sink_name=null_output" | sudo tee -a /etc/pulse/default.pa > /dev/null

# Reload systemd and enable service
echo "🔄 Reloading systemd daemon..."
sudo systemctl daemon-reload
sudo systemctl enable vocode.service

echo "✅ Service setup complete!"
echo ""
echo "To start the service:"
echo "  sudo systemctl start vocode.service"
echo ""
echo "To check status:"
echo "  sudo systemctl status vocode.service"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u vocode.service -f"

