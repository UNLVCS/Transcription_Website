# Meeting Minutes Generator - Production Deployment Guide

A production-ready AI-powered application that transcribes meeting audio, identifies speakers, and generates professional meeting minutes using Google Gemini AI.

## 🎯 Features

- **Multi-format Audio Support**: MP3, WAV, M4A, OGG, FLAC, and more
- **AI Transcription**: WhisperX for high-accuracy transcription
- **Speaker Diarization**: Automatic speaker identification using pyannote
- **AI-Generated Minutes**: Professional meeting minutes using Google Gemini
- **Real-time Progress**: Live progress tracking with time estimates
- **User Accounts**: Optional account system for job history tracking
- **Long Audio Support**: Process up to 24-hour recordings
- **Auto Cleanup**: Files automatically deleted after 30 days
- **PostgreSQL Storage**: Robust database for production use

## 📋 Prerequisites

### System Requirements

- **Operating System**: Ubuntu 20.04+ or similar Linux distribution
- **Python**: 3.9 or higher
- **PostgreSQL**: 12 or higher
- **CUDA** (optional but recommended): For GPU acceleration
- **ffmpeg**: Required for audio processing

### Minimum Hardware

- **CPU**: 4+ cores
- **RAM**: 8GB minimum, 16GB+ recommended
- **GPU**: NVIDIA GPU with 8GB+ VRAM recommended (optional)
- **Storage**: 50GB+ free space

## 🚀 Installation Steps

### 1. Install System Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3.9 python3.9-venv python3-pip -y

# Install PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# Install ffmpeg (required for audio processing)
sudo apt install ffmpeg -y

# Install CUDA (optional, for GPU acceleration)
# Follow: https://docs.nvidia.com/cuda/cuda-installation-guide-linux/
```

### 2. Set Up PostgreSQL Database

```bash
# Switch to postgres user
sudo -u postgres psql

# In PostgreSQL shell, create database and user:
CREATE DATABASE meeting_minutes;
CREATE USER meeting_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE meeting_minutes TO meeting_user;
\q
```

### 3. Clone/Upload Application Files

```bash
# Create application directory
sudo mkdir -p /var/www/meeting_minutes
cd /var/www/meeting_minutes

# Upload all application files here
# (app.py, templates/, requirements.txt, etc.)

# Set permissions
sudo chown -R $USER:$USER /var/www/meeting_minutes
```

### 4. Create Python Virtual Environment

```bash
cd /var/www/meeting_minutes

# Create virtual environment
python3.9 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### 5. Install Python Dependencies

```bash
# Install PyTorch (CPU version)
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu

# Or for GPU (CUDA 11.8):
# pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install other dependencies
pip install -r requirements.txt
```

**Note**: Installing all dependencies may take 10-20 minutes.

### 6. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env file
nano .env
```

Update the following in `.env`:

```env
SECRET_KEY=generate-a-random-secret-key-here
DATABASE_URL=postgresql://meeting_user:your_secure_password@localhost:5432/meeting_minutes
FLASK_ENV=production
```

To generate a secret key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 7. Initialize Database

```bash
# Activate virtual environment if not already active
source venv/bin/activate

# Initialize database tables
python3 -c "from app import init_db; init_db()"
```

### 8. Test the Application

```bash
# Run in development mode to test
python3 app.py

# In another terminal, test it:
curl http://localhost:5000
```

If successful, you should see the HTML response. Press Ctrl+C to stop.

## 🌐 Production Deployment

### Option 1: Using Gunicorn (Recommended)

Create a systemd service file:

```bash
sudo nano /etc/systemd/system/meeting-minutes.service
```

Add the following content:

```ini
[Unit]
Description=Meeting Minutes Generator
After=network.target postgresql.service

[Service]
Type=notify
User=YOUR_USERNAME
Group=www-data
WorkingDirectory=/var/www/meeting_minutes
Environment="PATH=/var/www/meeting_minutes/venv/bin"
ExecStart=/var/www/meeting_minutes/venv/bin/gunicorn --workers 4 --threads 2 --timeout 7200 --bind 0.0.0.0:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Replace `YOUR_USERNAME` with your actual username.

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable meeting-minutes
sudo systemctl start meeting-minutes
sudo systemctl status meeting-minutes
```

### Option 2: Using Screen (Simple Alternative)

```bash
# Install screen
sudo apt install screen -y

# Start a screen session
screen -S meeting-minutes

# Activate virtual environment
cd /var/www/meeting_minutes
source venv/bin/activate

# Run with gunicorn
gunicorn --workers 4 --threads 2 --timeout 7200 --bind 0.0.0.0:5000 app:app

# Detach from screen: Press Ctrl+A, then D
# Reattach: screen -r meeting-minutes
```

## 🔧 Nginx Reverse Proxy (Optional but Recommended)

Install and configure Nginx:

```bash
sudo apt install nginx -y

sudo nano /etc/nginx/sites-available/meeting-minutes
```

Add configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain or IP

    client_max_body_size 1G;  # Allow large file uploads

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 7200s;
        proxy_connect_timeout 7200s;
        proxy_send_timeout 7200s;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/meeting-minutes /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 🔑 How to Get API Keys

### 1. HuggingFace Token

Users need this for speaker diarization:

1. Go to https://huggingface.co/
2. Create a free account
3. Go to Settings → Access Tokens
4. Create a new token with "read" permissions
5. Copy the token (starts with `hf_`)
6. Accept the terms for pyannote models:
   - Visit https://huggingface.co/pyannote/speaker-diarization-3.0
   - Click "Agree and access repository"

### 2. Google Gemini API Key

Users need this for generating meeting minutes:

1. Go to https://aistudio.google.com/app/apikey
2. Sign in with Google account
3. Click "Create API Key"
4. Select or create a Google Cloud project
5. Copy the API key (starts with `AIza`)

**Free Tier**: Gemini offers generous free tier (60 requests/minute)

## 📊 Setting Up Automatic Cleanup

Create a cron job to clean up old files:

```bash
crontab -e
```

Add this line to run cleanup daily at 2 AM:

```cron
0 2 * * * curl http://localhost:5000/api/cleanup
```

## 🔍 Monitoring and Logs

### View Application Logs

```bash
# If using systemd:
sudo journalctl -u meeting-minutes -f

# If using screen:
screen -r meeting-minutes
```

### Monitor PostgreSQL

```bash
sudo -u postgres psql

# In PostgreSQL:
\c meeting_minutes
SELECT COUNT(*) FROM jobs;
SELECT status, COUNT(*) FROM jobs GROUP BY status;
```

### Disk Space Monitoring

```bash
# Check disk usage
df -h

# Check application directory size
du -sh /var/www/meeting_minutes/uploads
du -sh /var/www/meeting_minutes/outputs
```

## 🛠️ Troubleshooting

### Common Issues

**1. CUDA Out of Memory**
```bash
# Reduce batch size in app.py
# Change: batch_size=8 to batch_size=4
```

**2. Database Connection Error**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test connection
psql -U meeting_user -d meeting_minutes -h localhost
```

**3. Port Already in Use**
```bash
# Find what's using port 5000
sudo lsof -i :5000

# Kill the process if needed
sudo kill -9 <PID>
```

**4. Permission Errors**
```bash
# Fix directory permissions
sudo chown -R $USER:$USER /var/www/meeting_minutes
chmod -R 755 /var/www/meeting_minutes
```

**5. ffmpeg Not Found**
```bash
# Verify ffmpeg installation
which ffmpeg
ffmpeg -version

# Reinstall if needed
sudo apt install ffmpeg -y
```

## 📈 Performance Optimization

### For GPU Servers

Edit `app.py` to ensure GPU usage:
- Check `DEVICE_STR` is set to "cuda"
- Install CUDA-enabled PyTorch

### For Multi-GPU Servers

Set specific GPU:
```bash
export CUDA_VISIBLE_DEVICES=0  # Use GPU 0
# Or in systemd service file, add: Environment="CUDA_VISIBLE_DEVICES=0"
```

### Database Performance

```bash
sudo -u postgres psql

# In PostgreSQL, optimize:
ALTER DATABASE meeting_minutes SET work_mem = '256MB';
ALTER DATABASE meeting_minutes SET maintenance_work_mem = '512MB';
```

## 🔐 Security Recommendations

1. **Change default secret key** in `.env`
2. **Use HTTPS** in production (set up SSL with Let's Encrypt)
3. **Set up firewall**:
   ```bash
   sudo ufw allow 22      # SSH
   sudo ufw allow 80      # HTTP
   sudo ufw allow 443     # HTTPS
   sudo ufw enable
   ```
4. **Regular backups** of PostgreSQL database:
   ```bash
   pg_dump -U meeting_user meeting_minutes > backup.sql
   ```
5. **Keep system updated**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

## 📱 Usage Instructions for Users

### First Time Setup

1. Visit the application URL
2. (Optional) Create an account for job history tracking
3. Enter your HuggingFace token
4. Enter your Gemini API key
5. Check "Save keys in browser" for convenience

### Processing Audio

1. Click upload area or drag-and-drop audio file
2. Click "Start Processing"
3. Bookmark the job status page
4. Processing continues even if you close the browser
5. Download transcript and minutes when complete

### Supported Audio Formats

- MP3, WAV, M4A, OGG, FLAC, AAC, WMA
- Mono or stereo
- Any sample rate (converted to 16kHz automatically)
- Up to 24 hours duration
- Up to 1GB file size

## 🔄 Updating the Application

```bash
cd /var/www/meeting_minutes
source venv/bin/activate

# Pull new changes (if using git)
git pull

# Install any new dependencies
pip install -r requirements.txt

# Restart service
sudo systemctl restart meeting-minutes

# Or if using screen:
screen -r meeting-minutes
# Ctrl+C to stop, then restart: gunicorn ...
```

## 💾 Backup and Restore

### Backup Database

```bash
pg_dump -U meeting_user -h localhost meeting_minutes > backup_$(date +%Y%m%d).sql
```

### Restore Database

```bash
psql -U meeting_user -h localhost meeting_minutes < backup_20240101.sql
```

### Backup Files

```bash
tar -czf outputs_backup.tar.gz /var/www/meeting_minutes/outputs/
tar -czf uploads_backup.tar.gz /var/www/meeting_minutes/uploads/
```

## 📞 Support

For issues or questions:
1. Check logs: `sudo journalctl -u meeting-minutes -f`
2. Check PostgreSQL logs: `sudo tail -f /var/log/postgresql/postgresql-*.log`
3. Review troubleshooting section above

## 📄 License

This application uses the following open-source models:
- WhisperX (BSD-4-Clause)
- Pyannote.audio (MIT)
- Google Gemini (Google Cloud Terms)

Make sure to comply with all respective licenses when deploying.

---

**Built with ❤️ for efficient meeting transcription and documentation**
