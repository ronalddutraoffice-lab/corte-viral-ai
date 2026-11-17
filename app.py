import os, re, uuid, json, shutil, subprocess
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

ROOT = Path(__file__).parent
DATA = ROOT / "data"
UPLOADS = DATA / "uploads"
OUTPUTS = DATA / "outputs"
for p in (UPLOADS, OUTPUTS): p.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Corte Viral AI")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
templates = Jinja2Templates(directory=ROOT / "templates")
jobs = {}

def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr[-2500:])
    return p.stdout

def duration_of(path):
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "default=noprint_wrappers=1:nokey=1", str(path)])
    return float(out.strip())

def transcribe(path):
    from faster_whisper import WhisperModel
    model_name = os.getenv("WHISPER_MODEL", "tiny")
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(path), word_timestamps=True, vad_filter=True)
    result = []
    for s in segments:
        words = []
        if s.words:
            words = [{"start": w.start, "end": w.end, "word": w.word} for w in s.words]
        result.append({"start": s.start, "end": s.end, "text": s.text.strip(), "words": words})
    return result

HOOKS = ["inacreditável", "segredo", "ninguém", "nunca", "melhor", "pior", "erro", "atenção",
         "descobri", "resultado", "importante", "verdade", "por quê", "como", "dinheiro",
         "surpreendente", "problema", "solução", "cuidado"]

def choose_clips(segments, total, count, target):
    if not segments:
        # Fallback: evenly spaced cuts if speech recognition finds no speech.
        count = max(1, min(count, int(total // max(15, target)) or 1))
        return [{"start": max(0, (total/count)*i), "end": min(total, (total/count)*i + target),
                 "caption": "Trecho do vídeo"} for i in range(count)]
    candidates = []
    for i, s in enumerate(segments):
        text = s["text"].lower()
        score = min(len(text), 180) / 30
        score += sum(1.4 for h in HOOKS if h in text)
        score += 0.6 if "?" in text or "!" in text else 0
        # Prefer a complete thought; avoid very short transcript fragments.
        if len(text) < 28: score -= 1.2
        center = (s["start"] + s["end"]) / 2
        start = max(0, center - target * 0.38)
        end = min(total, start + target)
        start = max(0, end - target)
        candidates.append({"start": start, "end": end, "caption": s["text"], "score": score})
    candidates.sort(key=lambda x: x["score"], reverse=True)
    chosen = []
    for c in candidates:
        if all(c["end"] < x["start"] - 8 or c["start"] > x["end"] + 8 for x in chosen):
            chosen.append(c)
        if len(chosen) >= count: break
    if len(chosen) < count:
        for c in sorted(candidates, key=lambda x: x["start"]):
            if c not in chosen:
                chosen.append(c)
            if len(chosen) >= count: break
    return sorted(chosen[:count], key=lambda x: x["start"])

def make_srt(segments, start, end, out):
    rows, n = [], 1
    for s in segments:
        if s["end"] < start or s["start"] > end: continue
        a, b = max(s["start"], start)-start, min(s["end"], end)-start
        if b <= a: continue
        def ts(v):
            ms = int(v*1000); h=ms//3600000; ms%=3600000; m=ms//60000; ms%=60000; sec=ms//1000; ms%=1000
            return f"{h:02}:{m:02}:{sec:02},{ms:03}"
        rows.append(f"{n}\n{ts(a)} --> {ts(b)}\n{s['text']}\n")
        n += 1
    out.write_text("\n".join(rows), encoding="utf-8")

def process_job(job_id, source, count, target):
    try:
        jobs[job_id]["status"] = "Transcrevendo áudio com IA…"
        segments = transcribe(source)
        total = duration_of(source)
        clips = choose_clips(segments, total, count, target)
        result = []
        for i, c in enumerate(clips, 1):
            jobs[job_id]["status"] = f"Renderizando corte {i} de {len(clips)}…"
            stem = f"{job_id}_corte_{i:02}"
            srt = OUTPUTS / f"{stem}.srt"
            mp4 = OUTPUTS / f"{stem}.mp4"
            make_srt(segments, c["start"], c["end"], srt)
            # Vertical 9:16 center crop; subtitles burned in with readable styling.
            vf = ("scale=1080:1920:force_original_aspect_ratio=increase,"
                  "crop=1080:1920,setsar=1,"
                  f"subtitles='{str(srt).replace(chr(92), '/').replace(':', r'\\:')}'"
                  ":force_style='FontName=Arial,FontSize=18,PrimaryColour=&H00FFFFFF,"
                  "OutlineColour=&H00000000,BorderStyle=1,Outline=3,Shadow=1,"
                  "Alignment=2,MarginV=120'")
            run(["ffmpeg", "-y", "-ss", str(c["start"]), "-i", str(source), "-t",
                 str(c["end"]-c["start"]), "-vf", vf, "-c:v", "libx264",
                 "-preset", "veryfast", "-crf", "23", "-c:a", "aac", "-b:a", "128k",
                 "-movflags", "+faststart", str(mp4)])
            result.append({"name": mp4.name, "start": round(c["start"],1),
                           "end": round(c["end"],1), "caption": c["caption"]})
        jobs[job_id].update(status="Concluído", clips=result)
    except Exception as e:
        jobs[job_id].update(status="Erro no processamento", error=str(e))

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/create")
async def create(background_tasks: BackgroundTasks,
                 video: UploadFile = File(...),
                 youtube_url: str = Form(""),
                 count: int = Form(5),
                 length: int = Form(45)):
    if count < 1 or count > 20: raise HTTPException(400, "Escolha entre 1 e 20 cortes.")
    if length < 15 or length > 90: raise HTTPException(400, "Duração deve ser de 15 a 90 segundos.")
    suffix = Path(video.filename or "video.mp4").suffix.lower()
    if suffix not in {".mp4", ".mov", ".mkv", ".webm", ".avi"}:
        raise HTTPException(400, "Formato não suportado. Envie MP4, MOV, MKV, WEBM ou AVI.")
    jid = uuid.uuid4().hex[:10]
    src = UPLOADS / f"{jid}{suffix}"
    with src.open("wb") as f: shutil.copyfileobj(video.file, f)
    jobs[jid] = {"status": "Na fila", "clips": [], "youtube_url": youtube_url}
    background_tasks.add_task(process_job, jid, src, count, length)
    return {"job_id": jid}

@app.get("/api/status/{job_id}")
def status(job_id: str):
    if job_id not in jobs: raise HTTPException(404, "Projeto não encontrado.")
    return jobs[job_id]

@app.get("/download/{filename}")
def download(filename: str):
    path = OUTPUTS / filename
    if not path.exists() or path.parent != OUTPUTS: raise HTTPException(404, "Arquivo não encontrado.")
    return FileResponse(path, media_type="video/mp4", filename=filename)

@app.get("/health")
def health():
    return {"ok": True, "app": "Corte Viral AI"}
