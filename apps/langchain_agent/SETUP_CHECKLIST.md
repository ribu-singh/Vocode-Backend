# Telephony Server Setup Checklist

## Pre-Deployment

- [ ] Twilio account created
- [ ] Twilio phone number purchased
- [ ] Twilio Account SID and Auth Token obtained
- [ ] OpenAI API key obtained
- [ ] Deepgram API key obtained
- [ ] Azure Speech API key and region obtained
- [ ] GCP instance ready (or use existing client_backend instance)
- [ ] Domain name ready (optional, but recommended for HTTPS)

## Deployment Steps

- [ ] SSH into GCP instance
- [ ] Clone/upload vocode-core repository
- [ ] Install dependencies: `poetry install` in `apps/langchain_agent/`
- [ ] Set up Redis (Docker or system package)
- [ ] Create `/etc/vocode/telephony.env` with all required variables
- [ ] Get external IP or set up domain
- [ ] Update `TELEPHONY_SERVER_BASE_URL` in environment file
- [ ] Copy and configure `vocode-telephony.service`
- [ ] Update username in service file
- [ ] Start systemd service
- [ ] Configure firewall rules (ports 80, 443, and custom port if used)
- [ ] Set up Nginx reverse proxy (if using domain)
- [ ] Configure SSL certificate (Let's Encrypt)
- [ ] Configure Twilio webhook URL
- [ ] Test by calling Twilio number

## Environment Variables Required

```bash
TWILIO_ACCOUNT_SID=          # Required
TWILIO_AUTH_TOKEN=           # Required
TELEPHONY_SERVER_BASE_URL=   # Required (IP or domain)
OPENAI_API_KEY=              # Required
DEEPGRAM_API_KEY=            # Required
AZURE_SPEECH_KEY=            # Required
AZURE_SPEECH_REGION=         # Required
INBOUND_AGENT_PROMPT=        # Optional
INBOUND_AGENT_GREETING=      # Optional
```

## Quick Commands Reference

```bash
# Check service status
sudo systemctl status vocode-telephony.service

# View logs
sudo journalctl -u vocode-telephony.service -f

# Restart service
sudo systemctl restart vocode-telephony.service

# Check Redis
redis-cli ping

# Test endpoint locally
curl http://localhost:3001/inbound_call

# Test endpoint externally
curl https://your-domain/inbound_call
```

## Twilio Webhook URL Format

```
https://YOUR_TELEPHONY_SERVER_BASE_URL/inbound_call
```

Examples:
- `https://34.123.45.67/inbound_call` (using IP)
- `https://telephony.yourdomain.com/inbound_call` (using domain)

