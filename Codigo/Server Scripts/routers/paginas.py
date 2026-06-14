from fastapi import APIRouter
from fastapi.responses import HTMLResponse

# Crea un router per agrupar totes les rutes relacionades amb les pàgines estàtiques
router = APIRouter()

# Ruta arrel: pàgina principal (main.html)
@router.get("/")
async def get():
    # Obre el fitxer HTML del directori "static" i el retorna com a resposta HTML
    with open("static/main.html", "r") as f:
        return HTMLResponse(content=f.read())

# Ruta /historial: pàgina de l'historial de partides
@router.get("/historial")
async def get():
    with open("static/historial.html", "r") as f:
        return HTMLResponse(content=f.read())

# Ruta /control: panell de control en temps real (mapa, vídeo, puntuació)
@router.get("/control")
async def get():
    with open("static/control.html", "r") as f:
        return HTMLResponse(content=f.read())

# Ruta /creditos: pàgina amb crèdits del projecte
@router.get("/creditos")
async def get():
    with open("static/creditos.html", "r") as f:
        return HTMLResponse(content=f.read())

# Ruta /camara: pàgina per visualitzar només el stream de la càmera (utilitza encoding UTF-8 explícit)
@router.get("/camara")
async def get():
    with open("static/cam.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())