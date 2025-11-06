# GCP Compute Instance Deployment Guide

This guide will walk you through deploying your vocode-core application to a Google Cloud Platform Compute Instance.

## Prerequisites

- Google Cloud Platform account
- Google Cloud SDK (gcloud) installed locally
- Your project configured (`stream-conversation.py`)

## Step 1: Create a GCP Project and Enable APIs

1. **Create a new GCP project** (or use existing):
   ```bash
   gcloud projects create vocode-deployment --name="Vocode Deployment"
   gcloud config set project vocode-deployment
   ```

2. **Enable required APIs**:
   ```bash
   gcloud services enable compute.googleapis.com
   ```

## Step 2: Create a Compute Instance

1. **Create the VM instance**:
   ```bash
   gcloud compute instances create vocode-app \
     --zone=us-central1-a \
     --machine-type=e2-standard-2 \
     --image-family=ubuntu-2204-lts \
     --image-project=ubuntu-os-cloud \
     --boot-disk-size=20GB \
     --tags=http-server,https-server
   ```

2. **Allow firewall rules** (if needed):
   ```bash
   gcloud compute firewall-rules create allow-http \
     --allow tcp:80 \
     --source-ranges 0.0.0.0/0 \
     --target-tags http-server
   ```

## Step 3: Set Up the Instance

1. **SSH into the instance**:
   ```bash
   gcloud compute ssh vocode-app --zone=us-central1-a
   ```

2. **Update system packages**:
   ```bash
   sudo apt-get update
   sudo apt-get upgrade -y
   ```

3. **Install Python and dependencies**:
   ```bash
   sudo apt-get install -y python3.11 python3.11-venv python3-pip git curl
   sudo apt-get install -y libportaudio2 libportaudiocpp0 portaudio19-dev libasound-dev libsndfile1-dev ffmpeg
   ```

4. **Install Poetry**:
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
   source ~/.bashrc  # Reload shell configuration
   poetry --version  # Verify installation
   ```
   
   **Note**: If `poetry` command is not found after adding to `.bashrc`, run `source ~/.bashrc` or use the full path: `/home/YOUR_USERNAME/.local/bin/poetry`

## Step 4: Deploy Your Application

### Option A: Using Git (Recommended)

1. **Clone your repository**:
   ```bash
   git clone <your-repo-url> vocode-core
   cd vocode-core
   ```

2. **Install dependencies**:
   ```bash
   poetry install
   ```

### Option B: Using SCP (Direct Upload)

1. **From your local machine**, upload files:
   ```bash
   gcloud compute scp --recurse quickstarts/ vocode-app:~/vocode-core/quickstarts/ --zone=us-central1-a
   gcloud compute scp pyproject.toml poetry.lock vocode-app:~/vocode-core/ --zone=us-central1-a
   ```

   Then on the instance:
   ```bash
   mkdir -p ~/vocode-core
   cd ~/vocode-core
   poetry install
   ```

## Step 5: Set Up Environment Variables

1. **Create a service account file** (on the instance):
   ```bash
   sudo mkdir -p /etc/vocode
   sudo nano /etc/vocode/.env
   ```

2. **Add your environment variables**:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
   DEEPGRAM_API_KEY=your_deepgram_api_key_here
   ```

3. **Set secure permissions**:
   ```bash
   sudo chmod 600 /etc/vocode/.env
   sudo chown $USER:$USER /etc/vocode/.env
   ```

## Step 6: Create a Systemd Service

1. **Create service file**:
   ```bash
   sudo nano /etc/systemd/system/vocode.service
   ```

2. **Add the following content**:
   ```ini
   [Unit]
   Description=Vocode Streaming Application
   After=network.target

   [Service]
   Type=simple
   User=YOUR_USERNAME
   WorkingDirectory=/home/YOUR_USERNAME/vocode-core/quickstarts
   Environment="PATH=/home/YOUR_USERNAME/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
   EnvironmentFile=/etc/vocode/.env
   ExecStart=/home/YOUR_USERNAME/.local/bin/poetry run python stream-conversation.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

   **Replace `YOUR_USERNAME` with your actual username** (you can find it with `whoami`)

3. **Enable and start the service**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable vocode.service
   sudo systemctl start vocode.service
   ```

4. **Check status**:
   ```bash
   sudo systemctl status vocode.service
   ```

5. **View logs**:
   ```bash
   sudo journalctl -u vocode.service -f
   ```

## Step 7: Set Up Audio (for headless server)

Since this is a headless server, you'll need to configure audio:

1. **Install PulseAudio**:
   ```bash
   sudo apt-get install -y pulseaudio pulseaudio-utils alsa-utils
   ```

2. **Configure PulseAudio** for headless operation:
   ```bash
   sudo nano /etc/pulse/default.pa
   ```
   
   Add this line:
   ```
   load-module module-null-sink sink_name=null_output
   ```

3. **Set environment variables** for audio:
   ```bash
   sudo nano /etc/vocode/.env
   ```
   
   Add:
   ```
   PULSE_SERVER=unix:/tmp/pulse-socket
   ```

## Step 8: Secure Your Instance

1. **Set up firewall rules** (if needed):
   ```bash
   gcloud compute firewall-rules create allow-vocode --allow tcp:8080 --source-ranges YOUR_IP/32
   ```

2. **Set up SSH keys** (recommended):
   ```bash
   gcloud compute project-info add-metadata --metadata-from-file ssh-keys=~/.ssh/gcp_keys.pub
   ```

## Troubleshooting

### Check if the service is running:
```bash
sudo systemctl status vocode.service
```

### View logs:
```bash
sudo journalctl -u vocode.service -n 100 --no-pager
```

### Restart the service:
```bash
sudo systemctl restart vocode.service
```

### Check disk space:
```bash
df -h
```

### Check memory usage:
```bash
free -h
```

## Alternative: Docker Deployment

If you prefer Docker, you can use the provided Dockerfile:

1. **Build and push Docker image**:
   ```bash
   docker build -t gcr.io/vocode-deployment/vocode-app:latest .
   docker push gcr.io/vocode-deployment/vocode-app:latest
   ```

2. **Run on Compute Engine**:
   ```bash
   gcloud compute instances create-with-container vocode-app \
     --container-image=gcr.io/vocode-deployment/vocode-app:latest \
     --zone=us-central1-a \
     --machine-type=e2-standard-2
   ```

## Next Steps

- Set up monitoring with Cloud Monitoring
- Configure automatic backups
- Set up a load balancer if needed
- Configure custom domains
- Set up SSL certificates

