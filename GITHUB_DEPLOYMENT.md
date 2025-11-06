# GitHub Deployment Guide

This guide will help you deploy your vocode-core project to a new public GitHub repository.

## Prerequisites

- Git installed locally
- GitHub account
- All API keys removed from code (✅ Done)

## Step 1: Verify Security

✅ **API Keys Removed**: All hardcoded API keys have been replaced with placeholders
✅ **`.gitignore` Configured**: `.env` files are excluded from version control

## Step 2: Create .env File Locally (Don't Commit This!)

Create a `.env` file in the `quickstarts/` directory for local development:

```bash
cd quickstarts
cp .env.example .env
# Edit .env with your actual API keys
```

## Step 3: Initialize Git Repository (if not already done)

```bash
# Check if git is already initialized
git status

# If not initialized, run:
git init
```

## Step 4: Stage Files for Commit

```bash
# Add all files except those in .gitignore
git add .

# Verify what will be committed (check that .env files are NOT included)
git status
```

**Important**: Make sure `.env` files are NOT in the staging area!

## Step 5: Create Initial Commit

```bash
git commit -m "Initial commit: Vocode streaming conversation app

- Streaming conversation implementation with ElevenLabs and Deepgram
- GCP deployment scripts and documentation
- Environment variable configuration via .env files
- Security: API keys removed from code"
```

## Step 6: Create GitHub Repository

1. Go to https://github.com/new
2. Fill in repository details:
   - **Repository name**: `vocode-streaming-app` (or your preferred name)
   - **Description**: "Voice-based LLM streaming conversation app using Vocode"
   - **Visibility**: Public ✅
   - **DO NOT** initialize with README, .gitignore, or license (we already have these)
3. Click "Create repository"

## Step 7: Connect Local Repository to GitHub

```bash
# Add the remote repository (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/vocode-streaming-app.git

# Verify remote was added
git remote -v
```

## Step 8: Push to GitHub

```bash
# Push to main branch
git branch -M main
git push -u origin main
```

## Step 9: Verify Deployment

1. Visit your repository on GitHub: `https://github.com/YOUR_USERNAME/vocode-streaming-app`
2. Verify that:
   - ✅ All code files are present
   - ✅ `.env` files are NOT visible (they're in .gitignore)
   - ✅ `.env.example` is visible (template file)
   - ✅ README and documentation are present

## Step 10: Add Repository Description

On GitHub, add:
- **Description**: "Voice-based LLM streaming conversation app using Vocode, OpenAI, ElevenLabs, and Deepgram"
- **Topics**: `vocode`, `voice-ai`, `llm`, `streaming`, `python`, `elevenlabs`, `deepgram`, `openai`

## Step 11: Create README.md (if needed)

If you want a custom README, create one:

```markdown
# Vocode Streaming Conversation App

A voice-based LLM streaming conversation application built with Vocode.

## Features

- Real-time voice conversation with LLM
- ElevenLabs text-to-speech synthesis
- Deepgram speech-to-text transcription
- OpenAI GPT integration

## Setup

1. Clone the repository
2. Install dependencies: `poetry install`
3. Copy `.env.example` to `.env` and add your API keys
4. Run: `python quickstarts/stream-conversation.py`

## Deployment

See `DEPLOYMENT_GCP.md` for GCP deployment instructions.
```

## Security Checklist

Before pushing, verify:

- [x] All API keys removed from code
- [x] `.env` files in `.gitignore`
- [x] `.env.example` provided as template
- [x] No credentials in commit history (if you had previous commits with keys, see below)

## If You Previously Committed API Keys

If you accidentally committed API keys before, you need to:

1. **Rotate your API keys immediately** - Generate new keys from each service
2. **Remove keys from git history** (if this is a new repo, just start fresh):
   ```bash
   # Option 1: Start fresh (recommended for new repos)
   rm -rf .git
   git init
   git add .
   git commit -m "Initial commit"
   
   # Option 2: Use git filter-branch or BFG Repo-Cleaner (advanced)
   ```

## Next Steps

- Set up GitHub Actions for CI/CD (optional)
- Add GitHub Secrets for deployment (if using Actions)
- Create releases/tags for versions
- Add issues templates and contribution guidelines

## Troubleshooting

### "Repository not found" error
- Check that the repository name matches
- Verify you have push access
- Try using SSH instead: `git remote set-url origin git@github.com:USERNAME/REPO.git`

### "Permission denied" error
- Set up SSH keys: https://docs.github.com/en/authentication/connecting-to-github-with-ssh
- Or use GitHub CLI: `gh auth login`

### Files not showing on GitHub
- Check `.gitignore` isn't excluding them
- Verify files were staged: `git status`
- Check file size limits (GitHub has 100MB file limit)

