# GCP Telephony Server Deployment Guide

This guide will help you deploy the Vocode Telephony Server to Google Cloud Platform for handling inbound and outbound phone calls via Twilio.

## Prerequisites

- Google Cloud Platform account
- GCP Compute Instance already set up (can be the same instance as client_backend)
- API keys for:
  - Twilio (Account SID and Auth Token)
  - OpenAI (for ChatGPT agent)
  - Deepgram (for speech transcription)
  - Azure (for speech synthesis)
- A Twilio phone number purchased

## Step 1: Deploy the Telephony Server Application

### Option A: Deploy via Git (Recommended)

1. **SSH into your GCP instance**:
   ```bash
   gcloud compute ssh YOUR_INSTANCE_NAME --zone=YOUR_ZONE
   ```

2. **Navigate to the project directory and install dependencies**:
   ```bash
   cd ~/vocode-core/apps/langchain_agent
   poetry install
   ```

### Option B: Deploy via SCP

1. **From your local machine**, upload the langchain_agent directory:
   ```bash
   gcloud compute scp --recurse apps/langchain_agent/ YOUR_INSTANCE_NAME:~/vocode-core/apps/langchain_agent/ --zone=YOUR_ZONE
   ```

## Step 2: Set Up Redis

The telephony server requires Redis for managing call configurations. You can run Redis in two ways:

### Option A: Using Docker (Recommended)

1. **Run Redis container**:
   ```bash
   docker run -d --name vocode-redis \
     --restart unless-stopped \
     -p 6379:6379 \
     redis:7.0.9-alpine
   ```

2. **Verify Redis is running**:
   ```bash
   docker ps | grep redis
   redis-cli ping  # Should return "PONG"
   ```

### Option B: Install Redis Directly

1. **Install Redis**:
   ```bash
   sudo apt-get update
   sudo apt-get install redis-server -y
   ```

2. **Start and enable Redis**:
   ```bash
   sudo systemctl start redis-server
   sudo systemctl enable redis-server
   ```

3. **Verify Redis is running**:
   ```bash
   redis-cli ping  # Should return "PONG"
   ```

## Step 3: Configure Environment Variables

1. **Create or update the environment file** on your GCP instance:
   ```bash
   sudo nano /etc/vocode/telephony.env
   ```

2. **Add the following variables**:
   ```bash
   # Twilio Configuration (REQUIRED)
   TWILIO_ACCOUNT_SID=your_twilio_account_sid
   TWILIO_AUTH_TOKEN=your_twilio_auth_token
   
   # Telephony Server Base URL (REQUIRED)
   # Use your GCP instance's external IP or domain
   # Format: IP_OR_DOMAIN (without https://)
   # Example: 34.123.45.67 or telephony.yourdomain.com
   TELEPHONY_SERVER_BASE_URL=YOUR_EXTERNAL_IP_OR_DOMAIN
   
   # OpenAI Configuration (REQUIRED for ChatGPT agent)
   OPENAI_API_KEY=your_openai_api_key
   
   # Deepgram Configuration (REQUIRED for transcription)
   DEEPGRAM_API_KEY=your_deepgram_api_key
   
   # Azure Configuration (REQUIRED for speech synthesis)
   AZURE_SPEECH_KEY=your_azure_speech_key
   AZURE_SPEECH_REGION=your_azure_region
   
   # Optional: Customize agent behavior
   INBOUND_AGENT_PROMPT=The assistant helps callers and keeps responses concise and friendly.
   INBOUND_AGENT_GREETING=Hi there! How can I help you today?
   
   # Redis Configuration (if Redis is on different host)
   # REDIS_HOST=localhost
   # REDIS_PORT=6379
   ```

3. **Set secure permissions**:
   ```bash
   sudo chmod 600 /etc/vocode/telephony.env
   ```

## Step 4: Get Your Server's Public URL

1. **Get your instance's external IP** (from local machine):
   ```bash
   gcloud compute instances describe YOUR_INSTANCE_NAME --zone=YOUR_ZONE --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
   ```

   Or check in GCP Console: Compute Engine → VM instances → your instance → External IP

2. **Set TELEPHONY_SERVER_BASE_URL**:
   - If using IP: `TELEPHONY_SERVER_BASE_URL=34.123.45.67` (your actual IP)
   - If using domain: `TELEPHONY_SERVER_BASE_URL=telephony.yourdomain.com`

## Step 5: Set Up Systemd Service

1. **Copy the service file**:
   ```bash
   sudo cp ~/vocode-core/apps/langchain_agent/vocode-telephony.service /etc/systemd/system/
   ```

2. **Edit the service file** to match your username:
   ```bash
   sudo nano /etc/systemd/system/vocode-telephony.service
   ```
   
   Replace `YOUR_USERNAME` with your actual username (find it with `whoami`)

3. **Reload systemd and enable the service**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable vocode-telephony.service
   sudo systemctl start vocode-telephony.service
   ```

4. **Check the service status**:
   ```bash
   sudo systemctl status vocode-telephony.service
   ```

5. **View logs**:
   ```bash
   sudo journalctl -u vocode-telephony.service -f
   ```

## Step 6: Configure Firewall Rules

**Note**: Run these commands from your **local machine** (not from the GCP instance).

1. **Allow HTTP/HTTPS traffic** (ports 80 and 443) for Twilio webhooks:
   ```bash
   gcloud compute firewall-rules create allow-telephony-http \
     --allow tcp:80,tcp:443 \
     --source-ranges 0.0.0.0/0 \
     --target-tags http-server \
     --description "Allow HTTP/HTTPS for Twilio webhooks"
   ```

2. **If running on a custom port** (e.g., 3001), also allow that:
   ```bash
   gcloud compute firewall-rules create allow-telephony-custom \
     --allow tcp:3001 \
     --source-ranges 0.0.0.0/0 \
     --target-tags http-server \
     --description "Allow custom port for telephony server"
   ```

   **Note**: If your client_backend is already using port 3000, you'll need to run the telephony server on a different port (e.g., 3001). Update the service file accordingly.

## Step 7: Set Up SSL/HTTPS (Required for Production)

Twilio requires HTTPS for webhooks. You have two options:

### Option A: Using Nginx Reverse Proxy (Recommended)

1. **Install Nginx**:
   ```bash
   sudo apt-get update
   sudo apt-get install nginx certbot python3-certbot-nginx -y
   ```

2. **Create Nginx configuration**:
   ```bash
   sudo nano /etc/nginx/sites-available/telephony
   ```

3. **Add the following configuration** (replace with your domain):
   ```nginx
   server {
       listen 80;
       server_name telephony.yourdomain.com;  # Replace with your domain
       
       location / {
           proxy_pass http://localhost:3001;  # Or 3000 if not conflicting
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection 'upgrade';
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
           proxy_cache_bypass $http_upgrade;
       }
   }
   ```

4. **Enable the site**:
   ```bash
   sudo ln -s /etc/nginx/sites-available/telephony /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

5. **Set up SSL with Let's Encrypt**:
   ```bash
   sudo certbot --nginx -d telephony.yourdomain.com
   ```

6. **Update TELEPHONY_SERVER_BASE_URL**:
   ```bash
   sudo nano /etc/vocode/telephony.env
   # Change to: TELEPHONY_SERVER_BASE_URL=telephony.yourdomain.com
   sudo systemctl restart vocode-telephony.service
   ```

### Option B: Using GCP Load Balancer

1. Create a GCP Load Balancer with SSL certificate
2. Configure backend service to forward traffic from port 443 to your instance's telephony port
3. Use the load balancer's IP/domain as your `TELEPHONY_SERVER_BASE_URL`

## Step 8: Configure Twilio Webhook

1. **Log into your Twilio Console**: https://console.twilio.com/

2. **Navigate to Phone Numbers** → **Manage** → **Active Numbers**

3. **Click on your phone number**

4. **In the Voice & Fax section**, set the webhook URL:
   - **A CALL COMES IN**: `https://YOUR_TELEPHONY_SERVER_BASE_URL/inbound_call`
   - Example: `https://telephony.yourdomain.com/inbound_call` or `https://34.123.45.67/inbound_call`
   - **HTTP Method**: POST

5. **Click Save**

## Step 9: Test the Setup

1. **Check that the telephony server is running**:
   ```bash
   curl http://localhost:3001/inbound_call  # Should return TwiML or error
   ```

2. **Test from outside** (replace with your actual URL):
   ```bash
   curl https://telephony.yourdomain.com/inbound_call
   ```

3. **Call your Twilio phone number** - the AI agent should answer!

4. **Check logs**:
   ```bash
   sudo journalctl -u vocode-telephony.service -f
   ```

## Troubleshooting

### Service won't start
- Check logs: `sudo journalctl -u vocode-telephony.service -n 50`
- Verify environment variables: `sudo cat /etc/vocode/telephony.env`
- Check Redis is running: `redis-cli ping`

### Twilio webhook not working
- Verify firewall rules allow traffic on port 443
- Check Nginx is running: `sudo systemctl status nginx`
- Test webhook URL manually: `curl https://your-domain/inbound_call`
- Check Twilio webhook logs in Twilio Console

### Port conflicts
- If port 3000 is used by client_backend, change telephony server to port 3001
- Update the service file and restart: `sudo systemctl restart vocode-telephony.service`

### Redis connection errors
- Verify Redis is running: `redis-cli ping`
- Check Redis host/port in environment variables
- Test connection: `redis-cli -h localhost -p 6379 ping`

## Next Steps

- Customize the agent prompt and greeting via environment variables
- Set up call recording (if needed)
- Configure additional Twilio features
- Monitor call logs and transcripts

