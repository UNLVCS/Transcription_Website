import os
import gc
import uuid
import time
import json
import queue
from pathlib import Path
from threading import Thread
from datetime import datetime, timedelta

from flask import (
    Flask,
    request,
    render_template,
    send_from_directory,
    redirect,
    url_for,
    flash,
    jsonify,
    session,
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import text

# ML libraries are imported lazily to speed up startup
torch = None
whisperx = None
Pipeline = None
detect = None
DetectorFactory = None
genai = None
AudioSegment = None

def load_ml_libraries():
    """Lazy load ML libraries when needed for processing."""
    global torch, whisperx, Pipeline, detect, DetectorFactory, genai, AudioSegment, DEVICE_STR, DEVICE
    if torch is None:
        import torch as _torch
        torch = _torch
        DEVICE_STR = "cuda" if torch.cuda.is_available() else "cpu"
        DEVICE = torch.device(DEVICE_STR)
    if whisperx is None:
        import whisperx as _whisperx
        whisperx = _whisperx
    if Pipeline is None:
        from pyannote.audio import Pipeline as _Pipeline
        Pipeline = _Pipeline
    if detect is None:
        from langdetect import detect as _detect, DetectorFactory as _DetectorFactory
        detect = _detect
        DetectorFactory = _DetectorFactory
        DetectorFactory.seed = 0
    if genai is None:
        import google.generativeai as _genai
        genai = _genai
    if AudioSegment is None:
        from pydub import AudioSegment as _AudioSegment
        AudioSegment = _AudioSegment

# ---------- GLOBAL CONFIG ---------- #

DEVICE_STR = "cpu"  # Will be updated when ML libraries are loaded
DEVICE = None

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
CHUNKS_DIR = BASE_DIR / "chunks"

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
CHUNKS_DIR.mkdir(exist_ok=True)

CHUNK_LENGTH_MS = 60 * 1000  # 1 minute chunks

job_queue = queue.Queue()
AVG_JOB_DURATION_MINUTES = 15

# ---------- FLASK APP SETUP ---------- #

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "replace-with-a-secure-random-key-in-production")

# Database configuration - use SQLite for local development
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite:///meeting_minutes.db"
)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 3 * 1024 * 1024 * 1024  # 3GB max file size

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# ---------- DATABASE MODELS ---------- #

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    jobs = db.relationship("Job", backref="user", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Job(db.Model):
    __tablename__ = "jobs"

    id = db.Column(db.String(32), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    
    original_filename = db.Column(db.String(500))
    status = db.Column(db.String(50), default="queued", index=True)
    
    # Progress tracking
    current_stage = db.Column(db.String(200))
    progress_percent = db.Column(db.Integer, default=0)
    current_chunk = db.Column(db.Integer, default=0)
    total_chunks = db.Column(db.Integer, default=0)
    estimated_time_remaining = db.Column(db.Integer)  # seconds
    
    # File paths
    upload_path = db.Column(db.String(1000))
    conversation_path = db.Column(db.String(1000))
    minutes_path = db.Column(db.String(1000))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    started_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)
    
    # Error handling
    error = db.Column(db.Text)
    
    # Audio info
    duration_seconds = db.Column(db.Float)

    def _get_queue_position(self):
        """Return 1-based position among queued jobs, or 0 if not queued."""
        if self.status != "queued":
            return 0
        return Job.query.filter(
            Job.status == "queued",
            Job.created_at <= self.created_at,
        ).count()

    def to_dict(self):
        return {
            "id": self.id,
            "original_filename": self.original_filename,
            "status": self.status,
            "current_stage": self.current_stage,
            "progress_percent": self.progress_percent,
            "current_chunk": self.current_chunk,
            "total_chunks": self.total_chunks,
            "estimated_time_remaining": self.estimated_time_remaining,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "error": self.error,
            "duration_seconds": self.duration_seconds,
            "queue_position": self._get_queue_position(),
            "outputs": {
                "conversation": Path(self.conversation_path).name if self.conversation_path else None,
                "minutes": Path(self.minutes_path).name if self.minutes_path else None,
            }
        }


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---------- AUDIO PREPROCESSING ---------- #

def convert_to_wav(input_path: str, target_sample_rate: int = 16000) -> tuple:
    """
    Convert any audio file to mono WAV and return path + duration in seconds.
    """
    load_ml_libraries()
    audio = AudioSegment.from_file(input_path)
    duration_seconds = len(audio) / 1000.0
    
    audio = audio.set_frame_rate(target_sample_rate).set_channels(1)
    
    wav_path = OUTPUT_DIR / (Path(input_path).stem + "_converted.wav")
    audio.export(wav_path, format="wav")
    
    return str(wav_path), duration_seconds


def split_audio(audio_path, chunk_length_ms=60 * 1000):
    """Split audio into chunks and return list of chunk paths."""
    load_ml_libraries()
    audio = AudioSegment.from_wav(audio_path)
    chunks = []

    base_name = Path(audio_path).stem
    chunk_dir = CHUNKS_DIR / base_name
    chunk_dir.mkdir(parents=True, exist_ok=True)

    for i in range(0, len(audio), chunk_length_ms):
        chunk = audio[i:i + chunk_length_ms]
        chunk_path = chunk_dir / f"chunk_{i // chunk_length_ms}.wav"
        chunk.export(chunk_path, format="wav")
        chunks.append(str(chunk_path))

    return chunks


# ---------- MODEL LOADING ---------- #

def load_models(hf_token: str):
    """
    Load WhisperX and pyannote diarization models with user's HF token.
    """
    load_ml_libraries()
    whisper_model = whisperx.load_model("large-v2", device=DEVICE_STR, compute_type="float16")

    diarization_pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.0",
        use_auth_token=hf_token
    )
    if diarization_pipeline is None:
        raise ValueError("Failed to load diarization pipeline")

    diarization_pipeline = diarization_pipeline.to(DEVICE)
    return whisper_model, diarization_pipeline


# ---------- CHUNK PROCESSING ---------- #

def process_chunk(chunk_path, whisper_model, diarization_pipeline):
    """Process a single audio chunk: transcribe, align, and diarize."""
    load_ml_libraries()
    print(f"Transcribing {chunk_path}...")

    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        gc.collect()

    result = whisper_model.transcribe(
        chunk_path,
        task="transcribe",
        language=None,
        batch_size=8
    )

    detected_language = result.get("language", "unknown")
    print(f"Detected language: {detected_language}")

    if "segments" not in result or not result["segments"]:
        print(f"Warning: No segments for {chunk_path}")
        return []

    # Alignment
    try:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            gc.collect()

        model_a, metadata = whisperx.load_align_model(
            language_code=detected_language,
            device=DEVICE
        )
        aligned = whisperx.align(
            result["segments"], model_a, metadata, chunk_path, device=DEVICE
        )
        for seg in aligned["segments"]:
            try:
                seg["language"] = detect(seg["text"])
            except Exception:
                seg["language"] = detected_language
    except Exception as e:
        print(f"Alignment error for {chunk_path}: {e}")
        return result["segments"]

    # Diarization
    try:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            gc.collect()

        diarization = diarization_pipeline({"audio": chunk_path})
        speakers = list(diarization.labels())
        print(f"Detected {len(speakers)} speakers: {speakers}")

        diarize_segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            diarize_segments.append({
                "segment": {"start": turn.start, "end": turn.end},
                "speaker": speaker
            })

        if diarize_segments:
            speaker_segments = []
            for seg in aligned["segments"]:
                seg_start = seg["start"]
                seg_end = seg["end"]
                matching_speakers = []

                for d_seg in diarize_segments:
                    d_start = d_seg["segment"]["start"]
                    d_end = d_seg["segment"]["end"]
                    if max(seg_start, d_start) < min(seg_end, d_end):
                        matching_speakers.append(d_seg["speaker"])

                seg["speaker"] = (
                    max(set(matching_speakers), key=matching_speakers.count)
                    if matching_speakers
                    else "UNKNOWN"
                )
                speaker_segments.append(seg)

            return speaker_segments
        else:
            print("No diarization segments found")
            return aligned["segments"]

    except Exception as e:
        print(f"Diarization error for {chunk_path}: {e}")
        return aligned["segments"]


# ---------- TRANSCRIPT HELPERS ---------- #

def detect_language_safe(text):
    """Safely detect language, defaulting to English."""
    load_ml_libraries()
    try:
        detected_lang = detect(text)
        if detected_lang not in ["en", "es"]:
            return "en"
        return detected_lang
    except Exception:
        return "en"


def generate_conversation_transcript(segments):
    """
    Generate user-friendly conversation transcript.
    Format: [lang][start:end] Speaker N: text
    """
    if not segments:
        return "No conversation detected."

    segments.sort(key=lambda x: x["start"])

    speaker_map = {}
    for seg in segments:
        speaker = seg.get("speaker", "UNKNOWN")
        if speaker not in speaker_map:
            speaker_map[speaker] = len(speaker_map) + 1

    lines = []
    for seg in segments:
        language = detect_language_safe(seg["text"])
        speaker = seg.get("speaker", "UNKNOWN")
        speaker_num = speaker_map.get(speaker, "?")
        start = f"{seg['start']:.2f}"
        end = f"{seg['end']:.2f}"
        lines.append(f"[{language}][{start}:{end}] Speaker {speaker_num}: {seg['text']}")

    return "\n\n".join(lines)


# ---------- GEMINI: MINUTES GENERATION ---------- #

def generate_minutes_from_gemini(transcript_text: str, gemini_api_key: str) -> str:
    """
    Generate meeting minutes using Google Gemini API.
    """
    load_ml_libraries()
    try:
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""You are an expert assistant that creates professional, comprehensive meeting minutes from conversation transcripts.

Analyze the following meeting transcript and generate detailed, well-structured minutes:

TRANSCRIPT:
{transcript_text}

Please create professional meeting minutes with the following sections:

1. **Meeting Overview**
   - Date and Time (if mentioned or inferable)
   - Duration (if determinable)
   - Meeting Type/Purpose

2. **Attendees**
   - List all participants (identified as Speaker 1, Speaker 2, etc.)
   - Note any mentioned roles or titles

3. **Agenda & Topics Discussed**
   - Main topics covered
   - Order of discussion

4. **Key Discussion Points**
   - Summarize important conversations
   - Include different perspectives or opinions raised
   - Note any questions or concerns mentioned

5. **Decisions Made**
   - Clear list of all decisions
   - Who made the decision (if clear)
   - Rationale behind decisions (if provided)

6. **Action Items**
   - Specific tasks identified
   - Assigned to whom (Speaker N)
   - Deadlines or timeframes (if mentioned)
   - Priority level (if indicated)

7. **Open Issues & Follow-up**
   - Unresolved matters
   - Items requiring further discussion
   - Scheduled follow-ups

8. **Next Steps**
   - Planned next meetings
   - Immediate actions required

Please format the minutes professionally with clear headings, bullet points where appropriate, and concise but comprehensive summaries. If any section has no relevant information from the transcript, note it as "Not discussed" or "Not specified"."""

        response = model.generate_content(prompt)
        
        if response and response.text:
            return response.text
        else:
            return "Error: Gemini API returned an empty response."
            
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return f"Error generating minutes with Gemini API: {str(e)}\n\nPlease verify your API key is valid and has sufficient quota."


# ---------- PROGRESS UPDATE HELPER ---------- #

def update_job_progress(job_id: str, **kwargs):
    """Update job progress in database."""
    with app.app_context():
        try:
            job = Job.query.get(job_id)
            if job:
                for key, value in kwargs.items():
                    setattr(job, key, value)
                db.session.commit()
        except Exception as e:
            print(f"Error updating job progress: {e}")
            db.session.rollback()


# ---------- MAIN PIPELINE ---------- #

def run_pipeline(audio_path_original: str, output_prefix: str, job_id: str,
                 hf_token: str, gemini_api_key: str):
    """
    Complete pipeline: convert, transcribe, diarize, generate minutes.
    Updates progress in real-time.
    """
    import sys
    print(f"Starting pipeline for job {job_id}...", flush=True)
    sys.stdout.flush()
    try:
        print("Loading ML libraries...", flush=True)
        load_ml_libraries()  # Load ML libraries when processing starts
        print("ML libraries loaded successfully", flush=True)
        update_job_progress(
            job_id,
            status="running",
            started_at=datetime.utcnow(),
            current_stage="Converting audio to WAV format...",
            progress_percent=5
        )

        # Convert to WAV
        wav_path, duration = convert_to_wav(audio_path_original)
        update_job_progress(
            job_id,
            duration_seconds=duration,
            current_stage="Loading AI models...",
            progress_percent=10
        )

        # Load models
        whisper_model, diarization_pipeline = load_models(hf_token)
        update_job_progress(
            job_id,
            current_stage="Splitting audio into chunks...",
            progress_percent=15
        )

        # Split into chunks
        chunks = split_audio(wav_path, CHUNK_LENGTH_MS)
        total_chunks = len(chunks)
        update_job_progress(
            job_id,
            total_chunks=total_chunks,
            current_stage=f"Processing {total_chunks} audio chunks...",
            progress_percent=20
        )

        all_segments = []
        start_time = time.time()

        for i, chunk in enumerate(chunks):
            chunk_start = time.time()
            
            update_job_progress(
                job_id,
                current_chunk=i + 1,
                current_stage=f"Transcribing and analyzing chunk {i+1} of {total_chunks}...",
                progress_percent=20 + int((i / total_chunks) * 60)
            )

            segments = process_chunk(chunk, whisper_model, diarization_pipeline)
            
            if segments:
                offset = i * (CHUNK_LENGTH_MS / 1000)
                for seg in segments:
                    seg["start"] += offset
                    seg["end"] += offset
                all_segments.extend(segments)

            # Estimate time remaining
            elapsed = time.time() - start_time
            avg_time_per_chunk = elapsed / (i + 1)
            remaining_chunks = total_chunks - (i + 1)
            estimated_remaining = int(avg_time_per_chunk * remaining_chunks)
            
            update_job_progress(
                job_id,
                estimated_time_remaining=estimated_remaining
            )

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                gc.collect()

        # Generate outputs
        conversation_path = None
        minutes_path = None

        if all_segments:
            update_job_progress(
                job_id,
                current_stage="Generating conversation transcript...",
                progress_percent=85
            )

            conversation_transcript = generate_conversation_transcript(all_segments)
            conversation_path = OUTPUT_DIR / f"{output_prefix}_conversation.txt"
            with open(conversation_path, "w", encoding="utf-8") as f:
                f.write(conversation_transcript)

            update_job_progress(
                job_id,
                current_stage="Generating meeting minutes with AI...",
                progress_percent=90,
                conversation_path=str(conversation_path)
            )

            minutes_text = generate_minutes_from_gemini(conversation_transcript, gemini_api_key)
            minutes_path = OUTPUT_DIR / f"{output_prefix}_minutes.txt"
            with open(minutes_path, "w", encoding="utf-8") as f:
                f.write(minutes_text)

            update_job_progress(
                job_id,
                minutes_path=str(minutes_path)
            )

        update_job_progress(
            job_id,
            status="completed",
            current_stage="Processing complete!",
            progress_percent=100,
            finished_at=datetime.utcnow(),
            estimated_time_remaining=0
        )

    except Exception as e:
        import traceback
        print(f"Job {job_id} failed: {e}", flush=True)
        traceback.print_exc()
        update_job_progress(
            job_id,
            status="error",
            error=str(e),
            finished_at=datetime.utcnow(),
            current_stage=f"Error: {str(e)}"
        )


def run_pipeline_wrapper(audio_path_original: str, output_prefix: str, job_id: str,
                         hf_token: str, gemini_api_key: str):
    """Wrapper to catch any exceptions in the pipeline thread."""
    import traceback
    try:
        run_pipeline(audio_path_original, output_prefix, job_id, hf_token, gemini_api_key)
    except Exception as e:
        print(f"CRITICAL: Pipeline wrapper caught exception: {e}", flush=True)
        traceback.print_exc()


def queue_worker():
    """Process jobs one at a time from the queue."""
    while True:
        job_args = job_queue.get()
        if job_args is None:
            continue
        job_id = job_args['job_id']
        print(f"[Queue Worker] Starting job {job_id}", flush=True)
        run_pipeline_wrapper(
            job_args['audio_path'], job_args['output_prefix'],
            job_id, job_args['hf_token'], job_args['gemini_api_key'],
        )
        print(f"[Queue Worker] Finished job {job_id}", flush=True)
        job_queue.task_done()


# ---------- CLEANUP TASK ---------- #

def cleanup_old_files():
    """Delete files older than 30 days."""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        old_jobs = Job.query.filter(Job.created_at < cutoff_date).all()
        
        for job in old_jobs:
            # Delete files
            for path in [job.upload_path, job.conversation_path, job.minutes_path]:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception as e:
                        print(f"Error deleting {path}: {e}")
            
            # Delete chunk directory
            if job.upload_path:
                chunk_dir = CHUNKS_DIR / Path(job.upload_path).stem
                if chunk_dir.exists():
                    try:
                        import shutil
                        shutil.rmtree(chunk_dir)
                    except Exception as e:
                        print(f"Error deleting chunk dir {chunk_dir}: {e}")
            
            # Delete job from database
            db.session.delete(job)
        
        db.session.commit()
        print(f"Cleaned up {len(old_jobs)} old jobs")
        
    except Exception as e:
        print(f"Error in cleanup: {e}")
        db.session.rollback()


# ---------- ROUTES ---------- #

@app.route("/")
def index():
    """Home page - upload form."""
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """User registration."""
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        if not email or not password:
            flash("Email and password are required")
            return redirect(url_for("register"))
        
        if User.query.filter_by(email=email).first():
            flash("Email already registered")
            return redirect(url_for("register"))
        
        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash("Registration successful! Please login.")
        return redirect(url_for("login"))
    
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """User login."""
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard"))
        
        flash("Invalid email or password")
    
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    """User logout."""
    logout_user()
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    """User dashboard showing job history."""
    jobs = Job.query.filter_by(user_id=current_user.id).order_by(Job.created_at.desc()).all()
    return render_template("dashboard.html", jobs=jobs)


@app.route("/upload", methods=["POST"])
def upload():
    """Handle file upload and start processing."""
    if "audio_file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    audio_file = request.files["audio_file"]
    if not audio_file or audio_file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    
    hf_token = request.form.get("hf_token")
    gemini_key = request.form.get("gemini_key")
    
    if not hf_token or not gemini_key:
        return jsonify({"error": "HuggingFace token and Gemini API key are required"}), 400
    
    # Save uploaded file
    filename = secure_filename(audio_file.filename)
    job_id = uuid.uuid4().hex
    upload_path = UPLOAD_DIR / f"{job_id}_{filename}"
    audio_file.save(upload_path)
    
    # Create job record
    job = Job(
        id=job_id,
        user_id=current_user.id if current_user.is_authenticated else None,
        original_filename=filename,
        status="queued",
        upload_path=str(upload_path),
        current_stage="Queued for processing..."
    )
    db.session.add(job)
    db.session.commit()
    
    # Enqueue for sequential processing
    output_prefix = f"job_{job_id}"
    job_queue.put({
        'job_id': job_id,
        'audio_path': str(upload_path),
        'output_prefix': output_prefix,
        'hf_token': hf_token,
        'gemini_api_key': gemini_key,
    })
    print(f"Job {job_id} added to queue (queue size: {job_queue.qsize()})", flush=True)
    
    return jsonify({"job_id": job_id})


@app.route("/job/<job_id>")
def job_status_page(job_id):
    """Job status page with real-time updates."""
    job = Job.query.get(job_id)
    if not job:
        flash("Job not found")
        return redirect(url_for("index"))
    
    # Check if user owns this job (if logged in)
    if current_user.is_authenticated and job.user_id != current_user.id:
        flash("Access denied")
        return redirect(url_for("dashboard"))
    
    return render_template("job_status.html", job=job)


@app.route("/api/status/<job_id>")
def job_status_api(job_id):
    """API endpoint for job status updates."""
    job = Job.query.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    return jsonify(job.to_dict())


@app.route("/api/queue-status")
def queue_status_api():
    """API endpoint for global queue status."""
    queued_jobs = Job.query.filter_by(status="queued").order_by(Job.created_at).all()
    running_job = Job.query.filter_by(status="running").first()

    is_processing = running_job is not None
    queue_length = len(queued_jobs)

    # Estimate wait: remaining time on running job + queued jobs * avg duration
    estimated_wait_minutes = queue_length * AVG_JOB_DURATION_MINUTES
    running_job_info = None
    if running_job:
        running_job_info = {
            "id": running_job.id,
            "original_filename": running_job.original_filename,
            "progress_percent": running_job.progress_percent or 0,
        }
        # Add remaining time for running job
        remaining_fraction = 1 - (running_job.progress_percent or 0) / 100
        estimated_wait_minutes += remaining_fraction * AVG_JOB_DURATION_MINUTES

    estimated_wait_minutes = round(estimated_wait_minutes)

    return jsonify({
        "queue_length": queue_length,
        "is_processing": is_processing,
        "running_job": running_job_info,
        "estimated_wait_minutes": estimated_wait_minutes,
        "queued_jobs": [
            {"id": j.id, "original_filename": j.original_filename}
            for j in queued_jobs
        ],
    })


@app.route("/download/<job_id>/<file_type>")
def download_file(job_id, file_type):
    """Download conversation or minutes file."""
    job = Job.query.get(job_id)
    if not job:
        return "Job not found", 404
    
    # Check access
    if current_user.is_authenticated and job.user_id and job.user_id != current_user.id:
        return "Access denied", 403
    
    if file_type == "conversation" and job.conversation_path:
        return send_from_directory(
            OUTPUT_DIR,
            Path(job.conversation_path).name,
            as_attachment=True
        )
    elif file_type == "minutes" and job.minutes_path:
        return send_from_directory(
            OUTPUT_DIR,
            Path(job.minutes_path).name,
            as_attachment=True
        )
    
    return "File not found", 404


@app.route("/api/delete/<job_id>", methods=["DELETE"])
@login_required
def delete_job(job_id):
    """Delete a job and all its associated files."""
    import shutil

    job = Job.query.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    if job.user_id != current_user.id:
        return jsonify({"error": "Access denied"}), 403

    # Delete associated files
    for path in [job.upload_path, job.conversation_path, job.minutes_path]:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                print(f"Error deleting {path}: {e}")

    # Delete chunk directory
    if job.upload_path:
        chunk_dir = CHUNKS_DIR / Path(job.upload_path).stem
        if chunk_dir.exists():
            try:
                shutil.rmtree(chunk_dir)
            except Exception as e:
                print(f"Error deleting chunk dir {chunk_dir}: {e}")

    # Also try the converted WAV in outputs
    if job.upload_path:
        converted_wav = OUTPUT_DIR / (Path(job.upload_path).stem + "_converted.wav")
        if converted_wav.exists():
            try:
                os.remove(converted_wav)
            except Exception as e:
                print(f"Error deleting {converted_wav}: {e}")

    # Delete from database
    db.session.delete(job)
    db.session.commit()

    return jsonify({"status": "deleted"})


@app.route("/api/cleanup")
def trigger_cleanup():
    """Manual cleanup trigger (should be called by cron job)."""
    cleanup_old_files()
    return jsonify({"status": "cleanup completed"})


# ---------- DATABASE INITIALIZATION ---------- #

def init_db():
    """Initialize database tables."""
    with app.app_context():
        db.create_all()
        print("Database tables created successfully")


# ---------- MAIN ---------- #

def start_queue_worker():
    """Start worker thread and handle orphaned jobs from previous crashes."""
    with app.app_context():
        # Mark stuck "running" jobs as error
        for job in Job.query.filter_by(status="running").all():
            job.status = "error"
            job.error = "Server restarted while job was processing. Please re-upload."
            job.finished_at = datetime.utcnow()
        # Mark orphaned "queued" jobs as error (we lost their API keys)
        for job in Job.query.filter_by(status="queued").all():
            job.status = "error"
            job.error = "Server restarted while job was queued. Please re-upload."
            job.finished_at = datetime.utcnow()
        db.session.commit()

    worker = Thread(target=queue_worker, daemon=True, name="job-queue-worker")
    worker.start()

init_db()
start_queue_worker()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)

