from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from routers import paginas, raspberry, control, historial


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(paginas.router)
app.include_router(raspberry.router)
app.include_router(control.router)
app.include_router(historial.router)

for route in app.routes:
    if hasattr(route, "path"):
        print(f"Ruta registrada: {route.path}")
