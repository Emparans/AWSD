from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from routers import paginas, raspberry, control, historial, cam


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

#Carregar icona web
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.ico")

app.include_router(paginas.router)
app.include_router(raspberry.router)
app.include_router(control.router)
app.include_router(historial.router)
app.include_router(cam.router)

for route in app.routes:
    if hasattr(route, "path"):
        print(f"Ruta registrada: {route.path}")

