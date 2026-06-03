from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/")
async def get():
    with open("static/main.html", "r") as f:
        return HTMLResponse(content=f.read())

@router.get("/historial")
async def get():
    with open("static/historial.html", "r") as f:
        return HTMLResponse(content=f.read())

@router.get("/control")
async def get():
    with open("static/control.html", "r") as f:
        return HTMLResponse(content=f.read())

@router.get("/creditos")
async def get():
    with open("static/creditos.html", "r") as f:
        return HTMLResponse(content=f.read())