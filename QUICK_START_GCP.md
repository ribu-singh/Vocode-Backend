# Quick Reference: GCP Deployment Steps

> **Note**: This guide is for deploying the local streaming conversation app (`quickstarts/stream-conversation.py`).  
> For WebSocket server deployment, see [`apps/client_backend/DEPLOYMENT_GCP.md`](./apps/client_backend/DEPLOYMENT_GCP.md).

## TL;DR - Quick Deployment

1. **Create instance**:
   ```bash
   gcloud compute instances create vocode-app \
     --zone=us-central1-a \
     --machine-type=e2-standard-2 \
     --image-family=ubuntu-2204-lts \
     --image-project=ubuntu-os-cloud \
     --boot-disk-size=20GB
   ```

2. **SSH into instance**:
   ```bash
   gcloud compute ssh vocode-app --zone=us-central1-a
   ```

3. **Run setup** (on instance):
   ```bash
   # Install dependencies
   sudo apt-get update
   sudo apt-get install -y python3.11 python3-pip git curl \
       libportaudio2 libportaudiocpp0 portaudio19-dev libasound-dev \
       libsndfile1-dev ffmpeg pulseaudio

   # Install Poetry
   curl -sSL https://install.python-poetry.org | python3 -
   export PATH="$HOME/.local/bin:$PATH"

   # Clone/deploy your code
   git clone <your-repo-url> vocode-core
   cd vocode-core
   poetry install
   ```

4. **Set environment variables**:
   ```bash
   sudo mkdir -p /etc/vocode
   sudo nano /etc/vocode/.env
   # Add your API keys
   ```

5. **Set up service**:
   ```bash
   # Upload setup-service.sh and run it, or manually:
   sudo nano /etc/systemd/system/vocode.service
   # (copy config from DEPLOYMENT_GCP.md)
   sudo systemctl daemon-reload
   sudo systemctl enable vocode.service
   sudo systemctl start vocode.service
   ```

## Commands Cheat Sheet

### Check service status
```bash
sudo systemctl status vocode.service
```

### View logs
```bash
sudo journalctl -u vocode.service -f
```

### Restart service
```bash
sudo systemctl restart vocode.service
```

### Stop service
```bash
sudo systemctl stop vocode.service
```

### Update application
```bash
cd ~/vocode-core
git pull
poetry install
sudo systemctl restart vocode.service
```

## Important Notes

✅ **Security**: `stream-conversation.py` uses environment variables from `/etc/vocode/.env` or local `.env` files.  
✅ API keys should never be hardcoded in the code.

See [`DEPLOYMENT_GCP.md`](./DEPLOYMENT_GCP.md) for full detailed instructions.

