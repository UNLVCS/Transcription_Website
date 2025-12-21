import os
import gc
import uuid
import time
from pathlib import Path
from threading import Thread

from flask import (
    Flask,
    request,
    render_template_string,
    send_from_directory,
    redirect,
    url_for,
    flash,
    jsonify,
)
from werkzeug.utils import secure_filename

import torch
import whisperx
from pydub import AudioSegment
from pyannote.audio import Pipeline
from langdetect import detect, DetectorFactory
import requests

# ---------- GLOBAL CONFIG ---------- #

DetectorFactory.seed = 0  # deterministic language detection

DEVICE_STR = "cuda" if torch.cuda.is_available() else "cpu"
DEVICE = torch.device(DEVICE_STR)

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
CHUNKS_DIR = BASE_DIR / "chunks"

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
CHUNKS_DIR.mkdir(exist_ok=True)

CHUNK_LENGTH_MS = 60 * 1000  # 1 minute chunks

# Embedded Hugging Face token (as requested)
HUGGINGFACE_TOKEN = "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"

# Your LLM endpoint (Ollama-style API)
LLM_API_URL = "http://falcon9.cs.unlv.edu:11434/api/generate"

# Simple in-memory job store (use Redis/DB in production)
# job_id -> dict(status, outputs, error, times)
JOBS = {}


# ---------- AUDIO PREPROCESSING (ANY FORMAT → WAV) ---------- #

def convert_to_wav(input_path: str, target_sample_rate: int = 16000) -> str:
    """
    Takes any audio file (mp3, m4a, wav, etc.) and converts it to mono WAV.
    Requires ffmpeg installed and in PATH.
    """
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_frame_rate(target_sample_rate).set_channels(1)

    wav_path = OUTPUT_DIR / (Path(input_path).stem + "_converted.wav")
    audio.export(wav_path, format="wav")
    return str(wav_path)


def split_audio(audio_path, chunk_length_ms=60 * 1000):
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

def load_models():
    """
    Load WhisperX and pyannote diarization models.
    HF token is embedded.
    """
    whisper_model = whisperx.load_model("large-v2", device=DEVICE_STR)

    diarization_pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.0",
        use_auth_token=HUGGINGFACE_TOKEN
    )
    if diarization_pipeline is None:
        raise ValueError("Failed to load diarization pipeline - returned None")

    diarization_pipeline = diarization_pipeline.to(DEVICE)
    return whisper_model, diarization_pipeline


# ---------- CHUNK PROCESSING ---------- #

def process_chunk(chunk_path, whisper_model, diarization_pipeline):
    print(f"Transcribing {chunk_path}...")

    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        gc.collect()

    result = whisper_model.transcribe(
        chunk_path,
        task="transcribe",  # keep language, do not translate
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
    try:
        detected_lang = detect(text)
        if detected_lang not in ["en", "es"]:
            return "en"
        return detected_lang
    except Exception:
        return "en"


def generate_conversation_transcript(segments):
    """
    Output format:
    [lang][start:end] Speaker N: text
    """
    if not segments:
        return "No conversation detected."

    segments.sort(key=lambda x: x["start"])

    # Map internal speaker IDs to Speaker 1, 2, 3...
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


# ---------- LLM: MINUTES GENERATION ---------- #

def generate_minutes_from_llm(transcript_text: str) -> str:
    """
    Call your llama3.3:70b model hosted at falcon9.cs.unlv.edu:11434
    using the /api/generate endpoint (Ollama-style), non-streaming.
    """

    prompt = (
        "You are an assistant that writes clear, concise minutes of meetings.\n\n"
        "Here is the full conversation transcript:\n\n"
        f"{transcript_text}\n\n"
        "Please generate structured minutes with sections:\n"
        "1. Attendees\n"
        "2. Date & Time (if mentioned)\n"
        "3. Agenda\n"
        "4. Key Discussion Points\n"
        "5. Decisions Taken\n"
        "6. Action Items (with owner and due date if available)\n"
    )

    payload = {
        "model": "llama3.3:70b",
        "prompt": prompt,
        "stream": False,  # important: single JSON response
    }

    try:
        resp = requests.post(LLM_API_URL, json=payload, timeout=600)
        resp.raise_for_status()
        data = resp.json()

        # Ollama-style non-streaming response: text in "response"
        minutes = data.get("response", "")
        if not minutes:
            minutes = str(data)  # fallback
        return minutes

    except Exception as e:
        print(f"Error calling LLM: {e}")
        return (
            "Error: could not generate minutes from the LLM. "
            "Please check the LLM server at falcon9.cs.unlv.edu:11434 and try again."
        )


# ---------- MAIN PIPELINE USED BY BACKGROUND WORKER ---------- #

def run_pipeline(audio_path_original: str, output_prefix: str, job_id: str):
    """
    Pipeline:
    - convert to wav
    - load models
    - chunk, transcribe, diarize
    - build conversation transcript (user-friendly)
    - call LLM to generate minutes
    - save two txt files: conversation + minutes
    """
    try:
        JOBS[job_id]["status"] = "running"

        wav_path = convert_to_wav(audio_path_original)
        whisper_model, diarization_pipeline = load_models()

        chunks = split_audio(wav_path, CHUNK_LENGTH_MS)
        all_segments = []

        for i, chunk in enumerate(chunks):
            segments = process_chunk(chunk, whisper_model, diarization_pipeline)
            if not segments:
                continue

            offset = i * (CHUNK_LENGTH_MS / 1000)
            for seg in segments:
                seg["start"] += offset
                seg["end"] += offset

            all_segments.extend(segments)

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                gc.collect()

        conversation_path = None
        minutes_path = None

        if all_segments:
            # Conversation-style transcript
            conversation_transcript = generate_conversation_transcript(all_segments)
            conversation_path = OUTPUT_DIR / f"{output_prefix}_full_conversation_transcript.txt"
            with open(conversation_path, "w", encoding="utf-8") as f:
                f.write(conversation_transcript)

            # Minutes from LLM
            minutes_text = generate_minutes_from_llm(conversation_transcript)
            minutes_path = OUTPUT_DIR / f"{output_prefix}_meeting_minutes.txt"
            with open(minutes_path, "w", encoding="utf-8") as f:
                f.write(minutes_text)

        JOBS[job_id]["status"] = "done"
        JOBS[job_id]["finished_at"] = time.time()
        JOBS[job_id]["outputs"] = {
            "conversation": str(conversation_path.name) if conversation_path else None,
            "minutes": str(minutes_path.name) if minutes_path else None,
        }

    except Exception as e:
        JOBS[job_id]["status"] = "error"
        JOBS[job_id]["error"] = str(e)
        JOBS[job_id]["finished_at"] = time.time()
        print(f"Job {job_id} failed: {e}")


# ---------- FLASK APP & TEMPLATES ---------- #

app = Flask(__name__)
app.secret_key = "replace-with-a-better-secret"


TEMPLATE_INDEX = """
<!doctype html>
<html>
<head>
    <title>Meeting Minutes Generator</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; }
        .container { border: 1px solid #ddd; padding: 20px; border-radius: 8px; }
        .field { margin-bottom: 15px; }
        label { display: block; font-weight: bold; margin-bottom: 5px; }
        input[type="file"] { width: 100%; padding: 8px; }
        button { padding: 10px 20px; cursor: pointer; }
        .messages { color: red; margin-bottom: 15px; }
        .status-box { margin-top: 20px; padding: 10px; border-radius: 6px; background: #f9f9f9; }
        .note { font-size: 0.9em; color: #555; }
    </style>
</head>
<body>
<div class="container">
    <h1>Audio → Transcript → Meeting Minutes</h1>

    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <div class="messages">
          {% for msg in messages %}
            <div>{{ msg }}</div>
          {% endfor %}
        </div>
      {% endif %}
    {% endwith %}

    <form method="post" enctype="multipart/form-data">
        <div class="field">
            <label for="audio_file">Upload meeting audio (any format):</label>
            <input type="file" name="audio_file" id="audio_file" required>
        </div>

        <button type="submit">Start Processing</button>
        <div class="note">
            Processing runs on the server and can take time for long recordings.
            You will get a job link that you can reopen later to see progress and downloads.
        </div>
    </form>

    {% if job_id %}
        <hr>
        <div class="status-box">
            <h2>Job Started</h2>
            <p>Job ID: <code>{{ job_id }}</code></p>
            <p>
              <a href="{{ url_for('job_status_page', job_id=job_id) }}">
                  Open job status page
              </a>
            </p>
        </div>
    {% endif %}
</div>
</body>
</html>
"""


TEMPLATE_JOB_STATUS = """
<!doctype html>
<html>
<head>
    <title>Job {{ job_id }} Status</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; }
        .container { border: 1px solid #ddd; padding: 20px; border-radius: 8px; }
        .links a { display: block; margin-top: 8px; }
        .status { margin-top: 15px; padding: 10px; border-radius: 6px; background: #f4f4f4; }
        .note { font-size: 0.9em; color: #555; }
        .time { margin-top: 8px; font-size: 0.9em; color: #444; }
    </style>
    <script>
        const jobId = "{{ job_id }}";

        function formatSeconds(sec) {
            if (sec == null) return "";
            const s = Math.floor(sec % 60);
            const m = Math.floor((sec / 60) % 60);
            const h = Math.floor(sec / 3600);
            let out = "";
            if (h > 0) out += h + "h ";
            if (m > 0 || h > 0) out += m + "m ";
            out += s + "s";
            return out;
        }

        async function refreshStatus() {
            try {
                const resp = await fetch("/api/status/" + jobId);
                const data = await resp.json();
                const statusEl = document.getElementById("status-text");
                const linksEl = document.getElementById("links");
                const errorEl = document.getElementById("error-text");
                const timeEl = document.getElementById("time-text");

                statusEl.textContent = "Status: " + data.status;

                if (data.created_at && !data.finished_at) {
                    const now = Date.now() / 1000.0;
                    const elapsed = now - data.created_at;
                    timeEl.textContent = "Elapsed: " + formatSeconds(elapsed);
                } else if (data.created_at && data.finished_at) {
                    const elapsed = data.finished_at - data.created_at;
                    timeEl.textContent = "Total time: " + formatSeconds(elapsed);
                }

                if (data.status === "done") {
                    linksEl.innerHTML = "";
                    if (data.outputs.conversation) {
                        const a = document.createElement("a");
                        a.href = "/download/" + data.outputs.conversation;
                        a.textContent = "Download conversation transcript";
                        linksEl.appendChild(a);
                    }
                    if (data.outputs.minutes) {
                        const a = document.createElement("a");
                        a.href = "/download/" + data.outputs.minutes;
                        a.textContent = "Download meeting minutes";
                        linksEl.appendChild(a);
                    }
                } else if (data.status === "error") {
                    errorEl.textContent = "Error: " + (data.error || "unknown");
                }
            } catch (e) {
                console.log("Error fetching status", e);
            }
        }

        setInterval(refreshStatus, 5000);
        window.onload = refreshStatus;
    </script>
</head>
<body>
<div class="container">
    <h1>Job Status</h1>
    <p>Job ID: <code>{{ job_id }}</code></p>

    <div class="status">
        <div id="status-text">Status: {{ status }}</div>
        <div id="time-text" class="time"></div>
        <div id="error-text" style="color:red;"></div>
    </div>

    <div id="links" class="links">
        {% if outputs %}
            {% if outputs.conversation %}
                <a href="{{ url_for('download_file', filename=outputs.conversation) }}">Download conversation transcript</a>
            {% endif %}
            {% if outputs.minutes %}
                <a href="{{ url_for('download_file', filename=outputs.minutes) }}">Download meeting minutes</a>
            {% endif %}
        {% endif %}
    </div>

    <p class="note">
        This page updates automatically. Processing continues on the server even if you close the browser
        and later reopen this link from your history or bookmark.
    </p>
</div>
</body>
</html>
"""


# ---------- ROUTES ---------- #

@app.route("/", methods=["GET", "POST"])
def index():
    job_id = None

    if request.method == "POST":
        if "audio_file" not in request.files:
            flash("Please upload an audio file.")
            return redirect(request.url)

        audio_file = request.files["audio_file"]

        if not audio_file or audio_file.filename == "":
            flash("No file selected.")
            return redirect(request.url)

        filename = secure_filename(audio_file.filename)
        upload_path = UPLOAD_DIR / filename
        audio_file.save(upload_path)

        job_id = uuid.uuid4().hex
        output_prefix = f"job_{job_id}"

        JOBS[job_id] = {
            "status": "queued",
            "created_at": time.time(),
            "started_at": None,
            "finished_at": None,
            "outputs": None,
            "error": None,
        }

        # Start background processing
        t = Thread(
            target=run_pipeline,
            args=(str(upload_path), output_prefix, job_id),
            daemon=True,
        )
        JOBS[job_id]["started_at"] = time.time()
        t.start()

    return render_template_string(TEMPLATE_INDEX, job_id=job_id)


@app.route("/job/<job_id>")
def job_status_page(job_id):
    job = JOBS.get(job_id)
    if not job:
        return f"Job {job_id} not found", 404
    return render_template_string(
        TEMPLATE_JOB_STATUS,
        job_id=job_id,
        status=job["status"],
        outputs=job.get("outputs"),
    )


@app.route("/api/status/<job_id>")
def job_status_api(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "job not found"}), 404

    return jsonify({
        "status": job["status"],
        "outputs": job.get("outputs"),
        "error": job.get("error"),
        "created_at": job.get("created_at"),
        "started_at": job.get("started_at"),
        "finished_at": job.get("finished_at"),
    })


@app.route("/download/<path:filename>")
def download_file(filename):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)


if __name__ == "__main__":
    # Run with: python app.py
    # Then open http://127.0.0.1:5000
    app.run(debug=True, port=5002)




#CUDA_VISIBLE_DEVICES=1 python app.py
