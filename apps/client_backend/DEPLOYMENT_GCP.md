# GCP WebSocket Server Deployment Guide

This guide will help you deploy the Vocode WebSocket server to Google Cloud Platform for real-time conversation streaming.

## Prerequisites

- Google Cloud Platform account
- GCP Compute Instance already set up
- API keys for OpenAI, Deepgram, and ElevenLabs

## Step 1: Deploy the Client Backend Application

### Option A: Deploy via Git (Recommended)

1. **SSH into your GCP instance**:
   ```bash
   gcloud compute ssh YOUR_INSTANCE_NAME --zone=YOUR_ZONE
   ```
   
   Replace `YOUR_INSTANCE_NAME` and `YOUR_ZONE` with your actual instance name and zone.

2. **Navigate to the project directory and install dependencies**:
   ```bash
   cd ~/vocode-core/apps/client_backend
   poetry install
   ```
   
   > **Note**: The `pyproject.toml` should already include `fastapi` and `uvicorn`. If you encounter "Command not found: uvicorn", see the troubleshooting section.

### Option B: Deploy via SCP

1. **From your local machine**, upload the client_backend directory:
   ```bash
   gcloud compute scp --recurse apps/client_backend/ YOUR_INSTANCE_NAME:~/vocode-core/apps/client_backend/ --zone=YOUR_ZONE
   ```
   
   Replace `YOUR_INSTANCE_NAME` and `YOUR_ZONE` with your actual instance name and zone.

## Step 2: Configure Environment Variables

1. **Update the environment file** on your GCP instance:
   ```bash
   sudo nano /etc/vocode/.env
   ```

2. **Add/verify the following variables**:
   ```bash
   OPENAI_API_KEY=your_openai_api_key
   DEEPGRAM_API_KEY=your_deepgram_api_key
   ELEVENLABS_API_KEY=your_elevenlabs_api_key
   
   # Optional: Restrict CORS origins (comma-separated)
   # Leave as "*" to allow all origins, or specify: "https://yourdomain.com,https://app.yourdomain.com"
   ALLOWED_ORIGINS=*
   ```

3. **Set secure permissions**:
   ```bash
   sudo chmod 600 /etc/vocode/.env
   ```

## Step 3: Set Up Systemd Service

1. **Copy the service file**:
   ```bash
   sudo cp ~/vocode-core/apps/client_backend/vocode-websocket.service /etc/systemd/system/
   ```

2. **Edit the service file** to match your username:
   ```bash
   sudo nano /etc/systemd/system/vocode-websocket.service
   ```
   
   Replace `YOUR_USERNAME` with your actual username (find it with `whoami`)

3. **Reload systemd and enable the service**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable vocode-websocket.service
   sudo systemctl start vocode-websocket.service
   ```

4. **Check the service status**:
   ```bash
   sudo systemctl status vocode-websocket.service
   ```

5. **View logs**:
   ```bash
   sudo journalctl -u vocode-websocket.service -f
   ```

## Step 4: Configure Firewall Rules

**Note**: Run these commands from your **local machine** (not from the GCP instance), as the instance may not have sufficient IAM permissions.

1. **Allow WebSocket traffic** (port 3000):
   ```bash
   # Run this from your LOCAL machine (not from the GCP instance)
   gcloud compute firewall-rules create allow-websocket \
     --allow tcp:3000 \
     --source-ranges 0.0.0.0/0 \
     --target-tags http-server \
     --description "Allow WebSocket connections on port 3000"
   ```

   **Alternative**: Use GCP Console (VPC network → Firewall → Create Firewall Rule)

   **Note**: For production, restrict `--source-ranges` to specific IPs or use a load balancer with SSL.

2. **Verify firewall rule** (from local machine):
   ```bash
   gcloud compute firewall-rules list --filter="name:allow-websocket"
   ```

## Step 5: Get Your Server URL

1. **Get your instance's external IP** (from local machine):
   ```bash
   gcloud compute instances describe YOUR_INSTANCE_NAME --zone=YOUR_ZONE --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
   ```
   
   Or check in GCP Console: Compute Engine → VM instances → your instance → External IP

2. **Your WebSocket endpoint will be**:
   ```
   ws://YOUR_EXTERNAL_IP:3000/conversation
   ```

   Or if you've set up a domain with SSL:
   ```
   wss://yourdomain.com/conversation
   ```

## Step 6: Set Up SSL/HTTPS (Recommended for Production)

For production use, you should set up SSL/TLS:

### Option A: Using a GCP Load Balancer

1. **Create a GCP Load Balancer** with SSL certificate
2. **Configure backend service** to forward traffic from port 443 to your instance's port 3000
3. **Configure health checks** for your backend
4. **Use WSS (WebSocket Secure)**: `wss://yourdomain.com/conversation`

> **Note**: Load balancer setup is complex and beyond the scope of this guide. Refer to [GCP Load Balancer documentation](https://cloud.google.com/load-balancing/docs/load-balancing-overview).

### Option B: Using Nginx Reverse Proxy

1. **Install Nginx**:
   ```bash
   sudo apt-get install nginx certbot python3-certbot-nginx
   ```

2. **Configure Nginx** for WebSocket:
   ```nginx
   server {
       listen 80;
       server_name yourdomain.com;
       
       location /conversation {
           proxy_pass http://localhost:3000;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

3. **Set up SSL**:
   ```bash
   sudo certbot --nginx -d yourdomain.com
   ```

## Step 7: Test Your WebSocket Server

### Using Python Client

1. **Use the example client** from the `clients/` directory:
   ```bash
   python clients/websocket_client_with_audio.py ws://YOUR_EXTERNAL_IP:3000/conversation
   ```

   Or create a simple test script:
   ```python
   import asyncio
   import websockets
   import json
   
   async def test():
       uri = "ws://YOUR_EXTERNAL_IP:3000/conversation"
       async with websockets.connect(uri) as websocket:
           # Send initial config
           start_msg = {
               "type": "websocket_audio_config_start",
               "input_audio_config": {
                   "sampling_rate": 16000,
                   "audio_encoding": "linear16",
                   "chunk_size": 4096
               },
               "output_audio_config": {
                   "sampling_rate": 16000,
                   "audio_encoding": "linear16"
               },
               "conversation_id": None,
               "subscribe_transcript": True
           }
           await websocket.send(json.dumps(start_msg))
           
           # Wait for ready
           response = await websocket.recv()
           print(f"Server response: {response}")
   
   asyncio.run(test())
   ```

### Using Browser Console

```javascript
const ws = new WebSocket('ws://YOUR_EXTERNAL_IP:3000/conversation');
ws.onopen = () => {
    ws.send(JSON.stringify({
        type: "websocket_audio_config_start",
        input_audio_config: {
            sampling_rate: 16000,
            audio_encoding: "linear16",
            chunk_size: 4096
        },
        output_audio_config: {
            sampling_rate: 16000,
            audio_encoding: "linear16"
        },
        conversation_id: null,
        subscribe_transcript: true
    }));
};
ws.onmessage = (event) => {
    console.log('Received:', JSON.parse(event.data));
};
```

## Step 8: Updating the Application After Code Changes

After pushing new code to your repository, follow these steps to update the server:

1. **SSH into your GCP instance**:
   ```bash
   gcloud compute ssh YOUR_INSTANCE_NAME --zone=YOUR_ZONE
   ```
   
   Replace `YOUR_INSTANCE_NAME` and `YOUR_ZONE` with your actual instance name and zone.

2. **Navigate to the project directory**:
   ```bash
   cd ~/vocode-core
   ```

3. **Pull the latest code**:
   ```bash
   git pull origin main
   # Or: git pull origin <your-branch-name>
   ```

4. **Install any new dependencies**:
   ```bash
   cd ~/vocode-core/apps/client_backend
   poetry install
   ```

5. **Restart the service** to apply changes:
   ```bash
   sudo systemctl restart vocode-websocket.service
   ```

6. **Verify the service is running**:
   ```bash
   sudo systemctl status vocode-websocket.service
   ```

7. **Check logs** to ensure everything started correctly:
   ```bash
   sudo journalctl -u vocode-websocket.service -n 50 --no-pager
   ```

### Quick Update Script

A ready-to-use update script is available in the repository. To use it:

1. **Copy the script** to your home directory (if not already there):
   ```bash
   cp ~/vocode-core/apps/client_backend/update-vocode.sh ~/update-vocode.sh
   chmod +x ~/update-vocode.sh
   ```

2. **Run the update script**:
   ```bash
   ~/update-vocode.sh
   ```

The script will automatically:
- Pull the latest code from the repository
- Install any new dependencies
- Restart the service
- Verify the service is running
- Display status information

> **Note**: The script uses `git pull origin main` by default. If you're using a different branch, edit the script or use the manual steps above.

## Troubleshooting

### Service won't start / "Command not found: uvicorn"

1. **Check logs**:
   ```bash
   sudo journalctl -u vocode-websocket.service -n 50 --no-pager
   ```

2. **Install missing dependencies**:
   ```bash
   cd ~/vocode-core/apps/client_backend
   poetry add fastapi "uvicorn[standard]"
   poetry install
   ```

3. **Verify uvicorn is available**:
   ```bash
   cd ~/vocode-core/apps/client_backend
   poetry run which uvicorn
   # Should output a path like: /home/ribu_singh/.local/share/pypoetry/venv/bin/uvicorn
   ```

4. **Check environment variables**:
   ```bash
   sudo cat /etc/vocode/.env
   ```

### WebSocket connection fails / Timeout errors

1. **Check if instance has the `http-server` tag** (from local machine):
   ```bash
   gcloud compute instances describe YOUR_INSTANCE_NAME --zone=YOUR_ZONE --format='get(tags.items)'
   ```
   
   If `http-server` is missing, add it:
   ```bash
   gcloud compute instances add-tags YOUR_INSTANCE_NAME --zone=YOUR_ZONE --tags=http-server
   ```

2. **Alternative: Create firewall rule without target tags** (applies to all instances):
   ```bash
   # From your local machine
   gcloud compute firewall-rules create allow-websocket-all \
     --allow tcp:3000 \
     --source-ranges 0.0.0.0/0 \
     --description "Allow WebSocket connections on port 3000 for all instances"
   ```

3. **Test from within the instance** (SSH into server):
   ```bash
   curl http://localhost:3000
   # Should return a response (even 404 is OK - means server is running)
   ```

4. **Check if service is running**:
   ```bash
   sudo systemctl status vocode-websocket.service
   ```

5. **Verify port is listening**:
   ```bash
   sudo netstat -tlnp | grep 3000
   # Should show: tcp 0 0 0.0.0.0:3000 LISTEN
   ```

6. **Check firewall rules** (from local machine):
   ```bash
   gcloud compute firewall-rules list --filter="allowed.ports:3000"
   ```

### CORS errors in browser

1. **Update ALLOWED_ORIGINS** in `/etc/vocode/.env`:
   ```bash
   ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
   ```

2. **Restart the service**:
   ```bash
   sudo systemctl restart vocode-websocket.service
   ```

## Security Considerations

1. **Restrict CORS origins** - Don't use `*` in production
2. **Use WSS (WebSocket Secure)** - Always use SSL/TLS in production
3. **Restrict firewall rules** - Limit access to specific IPs when possible
4. **Monitor logs** - Set up log monitoring and alerts
5. **Rate limiting** - Consider adding rate limiting for production use

## Next Steps

- Set up monitoring with Cloud Monitoring
- Configure automatic backups
- Set up a load balancer for high availability
- Add authentication/authorization if needed
- Set up log aggregation

