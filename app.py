import os, uuid, subprocess
from pathlib import Path
from fastapi import FastAPI, UploadFile, Form, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates

BASE = Path(__file__).parent
UPLOADS = BASE / 'uploads'
OUTPUTS = BASE / 'outputs'
UPLOADS.mkdir(exist_ok=True)
OUTPUTS.mkdir(exist_ok=True)
app = FastAPI(title='Corte Viral AI')
templates = Jinja2Templates(directory=str(BASE))

@app.get('/static/style.css')
async def stylesheet():
    return FileResponse(BASE / 'style.css', media_type='text/css')

@app.get('/', response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse('index.html', {'request': request, 'message': None})

@app.post('/process', response_class=HTMLResponse)
async def process(request: Request, video: UploadFile = None, youtube_url: str = Form('')):
    if not video or not video.filename:
        return templates.TemplateResponse('index.html', {'request': request, 'message': 'Envie um arquivo de vídeo. O link do YouTube fica apenas como referência nesta versão.'})
    suffix = Path(video.filename).suffix.lower()
    if suffix not in {'.mp4', '.mov', '.mkv', '.webm', '.avi'}:
        return templates.TemplateResponse('index.html', {'request': request, 'message': 'Formato não suportado. Use MP4, MOV, MKV, WEBM ou AVI.'})
    ident = uuid.uuid4().hex
    source = UPLOADS / f'{ident}{suffix}'
    with source.open('wb') as f:
        while chunk := await video.read(1024 * 1024):
            f.write(chunk)
    target = OUTPUTS / f'{ident}.mp4'
    cmd = ['ffmpeg', '-y', '-i', str(source), '-t', '30', '-vf', 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23', '-c:a', 'aac', '-b:a', '128k', str(target)]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception:
        return templates.TemplateResponse('index.html', {'request': request, 'message': 'Não foi possível processar este vídeo. Tente um arquivo menor e em formato MP4.'})
    return templates.TemplateResponse('index.html', {'request': request, 'message': 'Corte vertical de demonstração criado!', 'download': f'/download/{ident}'})

@app.get('/download/{ident}')
async def download(ident: str):
    path = OUTPUTS / f'{ident}.mp4'
    if not path.exists():
        return HTMLResponse('Arquivo não encontrado', status_code=404)
    return FileResponse(path, media_type='video/mp4', filename='corte-viral.mp4')
