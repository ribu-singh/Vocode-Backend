# Quick Reference: GCP Deployment Steps

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
   git clone <your-repo> vocode-core
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

⚠️ **Security**: Your API keys are currently hardcoded in `stream5.py`. Use environment variables instead!

Consider updating `stream5.py` to use:
```python
os.environ.get("OPENAI_API_KEY")
os.environ.get("ELEVENLABS_API_KEY")
os.environ.get("DEEPGRAM_API_KEY")
```

See `DEPLOYMENT_GCP.md` for full detailed instructions.

