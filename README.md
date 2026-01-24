# Meeting Minutes Generator

An AI-powered web application that transcribes meeting audio, identifies speakers, and generates professional meeting minutes using Google Gemini AI.

## Features

- **Multi-format Audio Support**: MP3, WAV, M4A, OGG, FLAC, and more
- **AI Transcription**: WhisperX for high-accuracy speech-to-text
- **Speaker Diarization**: Automatic speaker identification using pyannote
- **AI-Generated Minutes**: Professional meeting minutes using Google Gemini
- **Real-time Progress**: Live progress tracking with time estimates
- **User Accounts**: Optional account system for job history tracking

## Quick Start (Local Development)

### Prerequisites

- **Python**: 3.9 or higher
- **ffmpeg**: Required for audio processing
- **Git**: For cloning the repository

### Step 1: Clone the Repository

```bash
git clone https://github.com/UNLVCS/Transcription_Website.git
cd Transcription_Website
```

### Step 2: Install System Dependencies

**Ubuntu/Debian/WSL:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv ffmpeg -y
```

**macOS:**
```bash
brew install python ffmpeg
```

**Windows:**
- Install [Python 3.9+](https://www.python.org/downloads/)
- Install [ffmpeg](https://ffmpeg.org/download.html) and add to PATH
- Or use WSL (recommended) and follow Ubuntu instructions

### Step 3: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install --upgrade pip
```

### Step 4: Install Python Dependencies

```bash
# Install PyTorch (CPU version - works on any machine)
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu

# For GPU acceleration (NVIDIA CUDA 11.8):
# pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install all other dependencies
pip install -r requirements.txt
```

**Note:** Installing dependencies may take 10-20 minutes due to large ML libraries.

### Step 5: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` file (the default settings work for local development):
```env
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
DATABASE_URL=sqlite:///meeting_minutes.db
HOST=0.0.0.0
PORT=5000
```

Generate a secret key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### Step 6: Run the Application

```bash
source venv/bin/activate  # If not already activated
python app.py
```

The application will start at: **http://localhost:5000**

## Getting API Keys

You need two API keys to use this application:

### 1. HuggingFace Token (for speaker diarization)

1. Go to https://huggingface.co/ and create a free account
2. Go to **Settings** > **Access Tokens**
3. Click **New token** and create a token with "read" permissions
4. Copy the token (starts with `hf_`)
5. **Important**: Accept the model terms:
   - Visit https://huggingface.co/pyannote/speaker-diarization-3.0
   - Click "Agree and access repository"
   - Also accept terms for https://huggingface.co/pyannote/segmentation-3.0

### 2. Google Gemini API Key (for meeting minutes generation)

1. Go to https://aistudio.google.com/app/apikey
2. Sign in with your Google account
3. Click **Create API Key**
4. Select or create a Google Cloud project
5. Copy the API key (starts with `AIza`)

**Free Tier**: Gemini offers a generous free tier (60 requests/minute)

## Using the Application

1. Open http://localhost:5000 in your browser
2. (Optional) Create an account to track your job history
3. Enter your HuggingFace token and Gemini API key
4. Check "Save keys in browser" for convenience
5. Upload an audio file (drag-and-drop or click to select)
6. Click "Start Processing"
7. Wait for processing to complete (progress is shown in real-time)
8. Download the transcript and meeting minutes

### Supported Audio Formats

MP3, WAV, M4A, OGG, FLAC, AAC, WMA - up to 1GB, up to 24 hours duration

### Processing Times (Approximate)

| Audio Length | CPU Only | With GPU |
|--------------|----------|----------|
| 10 minutes   | 5-10 min | 2-5 min  |
| 1 hour       | 30-45 min | 15-20 min |
| 2 hours      | 1-1.5 hrs | 30-40 min |

## Project Structure

```
Transcription_Website/
├── app.py                    # Main Flask application
├── requirements.txt          # Python dependencies
├── .env.example              # Environment template
├── deploy.sh                 # One-command server deployment script
├── Dockerfile                # Docker image definition
├── docker-compose.yml        # Docker compose configuration
├── nginx.conf                # Nginx reverse proxy config
├── meeting-minutes.service   # Systemd service file
├── templates/                # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── job_status.html
│   ├── login.html
│   ├── register.html
│   └── dashboard.html
├── uploads/                  # Uploaded audio files (auto-created)
├── outputs/                  # Generated transcripts/minutes (auto-created)
├── chunks/                   # Temporary audio chunks (auto-created)
└── instance/                 # SQLite database (auto-created)
```

## Troubleshooting

### NumPy Compatibility Error
```
A module that was compiled using NumPy 1.x cannot be run in NumPy 2.x
```
**Solution:**
```bash
pip install "numpy<2"
```

### Missing matplotlib
```
ModuleNotFoundError: No module named 'matplotlib'
```
**Solution:**
```bash
pip install matplotlib
```

### ffmpeg Not Found
```
FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'
```
**Solution:**
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows: Download from https://ffmpeg.org/download.html and add to PATH
```

### CUDA Out of Memory (GPU)
If you get CUDA memory errors, edit `app.py` and reduce batch_size:
```python
# Change batch_size=8 to batch_size=4 or batch_size=2
result = whisper_model.transcribe(chunk_path, task="transcribe", language=None, batch_size=4)
```

### Port Already in Use
```bash
# Find what's using port 5000
lsof -i :5000

# Kill the process
kill -9 <PID>

# Or use a different port
PORT=5001 python app.py
```

### HuggingFace Model Access Denied
Make sure you:
1. Have a valid HuggingFace token
2. Accepted the terms for pyannote models at:
   - https://huggingface.co/pyannote/speaker-diarization-3.0
   - https://huggingface.co/pyannote/segmentation-3.0

## Server Deployment

### Quick Deploy (Recommended)

Run this single command on your server:
```bash
curl -sSL https://raw.githubusercontent.com/UNLVCS/Transcription_Website/main/deploy.sh | bash
```

Or manually:
```bash
git clone https://github.com/UNLVCS/Transcription_Website.git
cd Transcription_Website
bash deploy.sh
```

The script automatically:
- Checks system requirements
- Installs dependencies
- Configures environment
- Sets up systemd service

### Manual Production Setup

1. Use PostgreSQL instead of SQLite (update `DATABASE_URL` in `.env`)
2. Run with Gunicorn: `gunicorn --workers 4 --timeout 7200 --bind 0.0.0.0:5000 app:app`
3. Use Nginx as reverse proxy (see `nginx.conf`)
4. Set up as systemd service (see `meeting-minutes.service`)

## Technology Stack

- **Backend**: Flask 3.0
- **Database**: SQLite (local) / PostgreSQL (production)
- **Transcription**: WhisperX with large-v2 model
- **Speaker Diarization**: pyannote.audio 3.1
- **Meeting Minutes**: Google Gemini AI
- **Audio Processing**: pydub, ffmpeg

## Requirements

### Minimum Hardware
- **CPU**: 4+ cores
- **RAM**: 8GB minimum, 16GB+ recommended
- **Storage**: 10GB+ free space (for models and audio files)

### Recommended Hardware (for faster processing)
- **GPU**: NVIDIA GPU with 8GB+ VRAM
- **RAM**: 16GB+
- **SSD**: For faster file I/O

## License

This application uses the following open-source components:
- WhisperX (BSD-4-Clause)
- Pyannote.audio (MIT)
- Flask (BSD-3-Clause)

Google Gemini API usage is subject to Google Cloud Terms of Service.

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Submit a Pull Request

## Support

For issues or questions:
1. Check the Troubleshooting section above
2. Open an issue on GitHub
