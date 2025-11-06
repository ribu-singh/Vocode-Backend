#!/bin/bash

# GCP Deployment Script for Vocode
# This script helps automate the deployment process

set -e

echo "🚀 Starting Vocode GCP Deployment..."

# Configuration
PROJECT_ID=${GCP_PROJECT_ID:-"vocode-deployment"}
INSTANCE_NAME=${INSTANCE_NAME:-"vocode-app"}
ZONE=${ZONE:-"us-central1-a"}
MACHINE_TYPE=${MACHINE_TYPE:-"e2-standard-2"}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI is not installed. Please install it first."
    exit 1
fi

# Set the project
print_status "Setting GCP project to $PROJECT_ID"
gcloud config set project $PROJECT_ID

# Check if instance exists
if gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE &> /dev/null; then
    print_warning "Instance $INSTANCE_NAME already exists. Skipping creation."
else
    print_status "Creating compute instance $INSTANCE_NAME..."
    gcloud compute instances create $INSTANCE_NAME \
        --zone=$ZONE \
        --machine-type=$MACHINE_TYPE \
        --image-family=ubuntu-2204-lts \
        --image-project=ubuntu-os-cloud \
        --boot-disk-size=20GB \
        --tags=http-server,https-server
    
    print_status "Waiting for instance to be ready..."
    sleep 30
fi

# Get the username
USERNAME=$(gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="whoami" 2>/dev/null | tr -d '\r\n')

print_status "Detected username: $USERNAME"

# Prepare remote setup script
print_status "Preparing remote setup script..."
REMOTE_SCRIPT=$(cat <<'EOF'
#!/bin/bash
set -e

echo "📦 Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y python3.11 python3.11-venv python3-pip git curl \
    libportaudio2 libportaudiocpp0 portaudio19-dev libasound-dev libsndfile1-dev ffmpeg \
    pulseaudio pulseaudio-utils alsa-utils

echo "📦 Installing Poetry..."
if ! command -v poetry &> /dev/null; then
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
fi

echo "✅ System setup complete!"
EOF
)

# Upload setup script
print_status "Uploading setup script to instance..."
echo "$REMOTE_SCRIPT" | gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="cat > /tmp/setup.sh && chmod +x /tmp/setup.sh && bash /tmp/setup.sh"

# Upload application files
print_status "Uploading application files..."
gcloud compute scp --recurse quickstarts/ $INSTANCE_NAME:~/vocode-core/quickstarts/ --zone=$ZONE
gcloud compute scp pyproject.toml poetry.lock $INSTANCE_NAME:~/vocode-core/ --zone=$ZONE

# Install dependencies
print_status "Installing Python dependencies..."
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="
cd ~/vocode-core && \
export PATH=\"\$HOME/.local/bin:\$PATH\" && \
poetry install
"

print_status "✅ Deployment complete!"
print_status "Next steps:"
echo "  1. SSH into the instance: gcloud compute ssh $INSTANCE_NAME --zone=$ZONE"
echo "  2. Set up environment variables in /etc/vocode/.env"
echo "  3. Create and start the systemd service (see DEPLOYMENT_GCP.md)"

