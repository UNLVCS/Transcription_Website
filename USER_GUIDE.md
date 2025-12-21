# Quick Start Guide for Users

## 🎯 What This Application Does

This tool automatically:
1. Transcribes your meeting audio
2. Identifies different speakers
3. Generates professional meeting minutes with action items

## 🔑 Before You Start: Get Your API Keys

You'll need two free API keys to use this service:

### 1. HuggingFace Token (for speaker identification)

**Steps:**
1. Go to https://huggingface.co/join
2. Create a free account (takes 1 minute)
3. Go to https://huggingface.co/settings/tokens
4. Click "New token"
5. Give it a name like "meeting-transcription"
6. Select "Read" permissions
7. Click "Generate token"
8. **IMPORTANT**: Copy the token (starts with `hf_`)
9. Accept model terms:
   - Visit https://huggingface.co/pyannote/speaker-diarization-3.0
   - Click "Agree and access repository"
   - Visit https://huggingface.co/pyannote/segmentation-3.0
   - Click "Agree and access repository"

### 2. Google Gemini API Key (for generating minutes)

**Steps:**
1. Go to https://aistudio.google.com/app/apikey
2. Sign in with your Google account
3. Click "Get API key" → "Create API key"
4. Select or create a Google Cloud project
5. Copy the API key (starts with `AIza`)

**Free Tier**: Gemini offers 60 requests per minute for free!

## 📤 How to Use the Application

### Step 1: Open the Website
Navigate to your application URL (e.g., http://your-server-ip:5000)

### Step 2: Enter Your API Keys
- Paste your HuggingFace token
- Paste your Gemini API key
- ✅ Check "Save keys in browser" so you don't have to enter them again

### Step 3: Upload Your Audio File
- Click the upload area or drag & drop your file
- Supported formats: MP3, WAV, M4A, OGG, FLAC, etc.
- Maximum size: 1GB
- Maximum duration: 24 hours

### Step 4: Start Processing
- Click "🚀 Start Processing"
- You'll be redirected to a status page

### Step 5: Monitor Progress
The status page shows:
- ✅ Real-time progress percentage
- ⏱️ Current processing stage
- 📊 Time remaining estimate
- 🔢 Chunks processed

**TIP**: You can close the browser and come back later - processing continues on the server!

### Step 6: Download Your Results
When complete, you'll get two files:
1. **📄 Conversation Transcript**: Full verbatim transcript with speaker labels and timestamps
2. **📋 Meeting Minutes**: AI-generated professional summary with:
   - Attendees
   - Discussion points
   - Decisions made
   - Action items with owners

## 🎭 Optional: Create an Account

Benefits of creating an account:
- ✅ View all your past jobs
- ✅ Quick access to previous transcripts
- ✅ Track processing history
- ✅ 100% free, no credit card required

## 💡 Tips for Best Results

### Audio Quality
- ✅ Use clear audio recordings
- ✅ Minimize background noise
- ✅ Ensure speakers are audible
- ⚠️ Very noisy audio may affect accuracy

### File Formats
- **Best**: WAV (uncompressed)
- **Good**: FLAC, M4A
- **OK**: MP3 (higher bitrate is better)

### Processing Time
Approximate processing times:
- 1-hour audio: ~30-45 minutes
- 2-hour audio: ~1-1.5 hours
- 5-hour audio: ~2-3 hours

*Times vary based on server load and audio complexity*

## 🔒 Privacy & Security

- Your API keys are stored only in your browser
- Audio files are automatically deleted after 30 days
- Files are stored securely on the server
- Only you can access your job results (with job link)

## ❓ Troubleshooting

### "Invalid HuggingFace Token"
- Make sure you accepted the model terms (see Step 9 in HuggingFace setup)
- Verify token starts with `hf_`
- Try generating a new token

### "Invalid Gemini API Key"
- Verify key starts with `AIza`
- Check you haven't exceeded free tier limits
- Make sure the API key is enabled for Gemini

### "Processing Failed"
- Check audio file is valid and plays correctly
- Try a smaller audio file first
- Ensure audio is not corrupted
- Contact administrator if issue persists

### "Upload Failed"
- Check file size (max 1GB)
- Verify file is an audio format
- Try a different browser
- Check your internet connection

## 📋 Sample Output Format

### Transcript Example:
```
[en][0.00:2.50] Speaker 1: Good morning everyone, let's start the meeting.
[en][2.50:5.30] Speaker 2: Thanks for joining. I'll share the quarterly results.
[en][5.30:8.10] Speaker 1: Great, please go ahead.
```

### Minutes Example:
```
MEETING OVERVIEW
Date: January 15, 2024
Duration: 45 minutes

ATTENDEES
- Speaker 1 (Chair)
- Speaker 2 (Finance)
- Speaker 3 (Marketing)

KEY DISCUSSION POINTS
1. Q4 Financial Results
   - Revenue exceeded targets by 15%
   - Operating costs reduced by 8%

DECISIONS MADE
1. Approved Q1 marketing budget increase
2. Greenlit new product development

ACTION ITEMS
1. Speaker 2: Prepare detailed budget report by Jan 20
2. Speaker 3: Launch marketing campaign by Feb 1
3. Speaker 1: Schedule follow-up meeting for Jan 25
```

## 🆘 Need Help?

If you encounter any issues:
1. Check this guide first
2. Verify your API keys are correct
3. Try with a smaller test file
4. Contact your system administrator

---

**Ready to get started? Upload your first meeting audio now! 🚀**
