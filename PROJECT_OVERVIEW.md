# Meeting Minutes Generator - Production Ready Application

## 🎯 Project Overview

A complete, production-ready web application that uses AI to transcribe meeting audio, identify speakers, and generate professional meeting minutes. Built with Flask, PostgreSQL, WhisperX, and Google Gemini.

## 📁 Project Structure

```
meeting_minutes_app/
├── app.py                          # Main Flask application
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variables template
├── .gitignore                      # Git ignore rules
├── Dockerfile                      # Docker container configuration
├── docker-compose.yml              # Docker Compose orchestration
├── meeting-minutes.service         # Systemd service file
├── nginx.conf                      # Nginx reverse proxy config
├── setup_local.sh                  # Local setup automation script
│
├── templates/                      # HTML templates
│   ├── base.html                   # Base template with styling
│   ├── index.html                  # Upload page
│   ├── job_status.html             # Job progress tracking
│   ├── login.html                  # User login
│   ├── register.html               # User registration
│   └── dashboard.html              # User dashboard
│
├── uploads/                        # Uploaded audio files (created at runtime)
├── outputs/                        # Generated transcripts and minutes
├── chunks/                         # Temporary audio chunks
│
├── README.md                       # Complete deployment guide
├── USER_GUIDE.md                   # End-user instructions
└── DEPLOYMENT_CHECKLIST.md         # Deployment verification checklist
```

## 🚀 Key Features

### For Users
- **Multi-format Support**: MP3, WAV, M4A, OGG, FLAC, etc.
- **Drag & Drop Upload**: Intuitive file upload interface
- **Real-time Progress**: Live updates with time estimates
- **Speaker Identification**: Automatic speaker diarization
- **AI-Generated Minutes**: Professional summaries with action items
- **User Accounts**: Optional account system for history tracking
- **Long Audio Support**: Process up to 24 hours of audio
- **Auto-cleanup**: Files deleted after 30 days

### For Administrators
- **PostgreSQL Database**: Robust data storage
- **Production Ready**: Gunicorn + Nginx deployment
- **Docker Support**: Containerized deployment option
- **GPU Acceleration**: CUDA support for faster processing
- **Monitoring**: Comprehensive logging and status tracking
- **Security**: User authentication, secure file handling
- **Scalable**: Multi-worker architecture

## 🔑 Technologies Used

- **Backend**: Python 3.9+, Flask
- **Database**: PostgreSQL
- **AI Models**:
  - WhisperX (transcription)
  - Pyannote.audio (speaker diarization)
  - Google Gemini (minutes generation)
- **Audio Processing**: pydub, ffmpeg
- **Web Server**: Gunicorn + Nginx
- **Authentication**: Flask-Login

## 📋 Quick Start

### Local Testing (Development)

```bash
# 1. Navigate to project directory
cd meeting_minutes_app

# 2. Run setup script
chmod +x setup_local.sh
./setup_local.sh

# 3. Follow prompts and update .env file

# 4. Start application
source venv/bin/activate
python3 app.py

# 5. Open browser to http://localhost:5000
```

### Production Deployment

```bash
# 1. Upload files to server
scp -r meeting_minutes_app/ user@server:/var/www/

# 2. SSH into server
ssh user@server

# 3. Follow README.md deployment steps
# - Install system dependencies
# - Set up PostgreSQL
# - Configure environment
# - Set up systemd service
# - Configure Nginx

# 4. Start service
sudo systemctl start meeting-minutes

# 5. Verify
curl http://localhost:5000
```

## 🔐 Security Considerations

1. **API Keys**: Users provide their own keys (stored in browser)
2. **Authentication**: Optional user accounts with password hashing
3. **File Access**: Job-based access control
4. **Database**: Parameterized queries (SQLAlchemy ORM)
5. **Auto-cleanup**: Files deleted after 30 days
6. **HTTPS**: Nginx SSL/TLS support (configure separately)

## 📊 System Requirements

### Minimum
- CPU: 4 cores
- RAM: 8GB
- Storage: 50GB
- OS: Ubuntu 20.04+

### Recommended
- CPU: 8+ cores
- RAM: 16GB+
- Storage: 100GB+
- GPU: NVIDIA with 8GB+ VRAM
- OS: Ubuntu 22.04 LTS

## 🎯 Processing Capacity

### Approximate Times
- 1 hour audio: 30-45 minutes
- 2 hour audio: 1-1.5 hours
- 5 hour audio: 2-3 hours

### With GPU Acceleration
- 1 hour audio: 15-20 minutes
- 2 hour audio: 30-40 minutes
- 5 hour audio: 1-1.5 hours

*Times vary based on audio quality and server load*

## 🔄 Workflow

1. **User uploads audio file** with API keys
2. **System converts** to WAV format
3. **Audio is split** into 1-minute chunks
4. **Each chunk is processed**:
   - Transcribed (WhisperX)
   - Aligned (word-level timing)
   - Diarized (speaker identification)
5. **Segments are merged** with time offsets
6. **Conversation transcript** is generated
7. **Gemini AI** creates professional minutes
8. **Files are saved** to outputs directory
9. **User downloads** results

## 📈 Database Schema

### Users Table
- `id`: Primary key
- `email`: Unique email address
- `password_hash`: Bcrypt hashed password
- `created_at`: Account creation timestamp

### Jobs Table
- `id`: UUID job identifier
- `user_id`: Foreign key to users (nullable)
- `original_filename`: Original audio filename
- `status`: queued, running, completed, error
- `current_stage`: Text description of current step
- `progress_percent`: 0-100
- `current_chunk`: Current chunk being processed
- `total_chunks`: Total number of chunks
- `estimated_time_remaining`: Seconds
- `upload_path`: Path to uploaded file
- `conversation_path`: Path to transcript
- `minutes_path`: Path to minutes
- `created_at`, `started_at`, `finished_at`: Timestamps
- `error`: Error message if failed
- `duration_seconds`: Audio duration

## 🛠️ Maintenance Tasks

### Daily
- Monitor disk space
- Check application logs

### Weekly
- Review error logs
- Verify cleanup is working
- Check database size

### Monthly
- Update system packages
- Backup database
- Review user feedback

## 📞 Support & Troubleshooting

### Common Issues

1. **Database connection failed**
   - Check PostgreSQL is running
   - Verify credentials in .env
   - Test connection manually

2. **CUDA out of memory**
   - Reduce batch_size in app.py
   - Use CPU mode instead
   - Process smaller chunks

3. **Upload fails**
   - Check file size limit
   - Verify ffmpeg is installed
   - Check nginx client_max_body_size

4. **Processing hangs**
   - Check system resources
   - Review application logs
   - Restart service

### Log Locations
- **Application**: `sudo journalctl -u meeting-minutes -f`
- **Nginx**: `/var/log/nginx/error.log`
- **PostgreSQL**: `/var/log/postgresql/`

## 🎓 Documentation Files

- **README.md**: Complete deployment guide for administrators
- **USER_GUIDE.md**: Instructions for end users
- **DEPLOYMENT_CHECKLIST.md**: Step-by-step deployment verification

## 🤝 Contributing

This is a production application. Before making changes:
1. Test in development environment
2. Update documentation
3. Test with various audio files
4. Verify database migrations
5. Update version numbers

## 📄 License Compliance

Ensure compliance with:
- WhisperX: BSD-4-Clause
- Pyannote.audio: MIT
- Google Gemini: Google Cloud Terms of Service

## 🎉 Credits

Built using:
- Flask web framework
- WhisperX for transcription
- Pyannote.audio for speaker diarization
- Google Gemini for AI-generated minutes
- PostgreSQL for data storage

---

**For detailed setup instructions, see README.md**
**For user instructions, see USER_GUIDE.md**
**For deployment verification, see DEPLOYMENT_CHECKLIST.md**
