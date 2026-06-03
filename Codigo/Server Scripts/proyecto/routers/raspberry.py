from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from pathlib import Path
import cv2
import numpy as np
import json

# Importamos la lista de websockets del otro archivo para poder avisarles
from .control import clientes_web 
import labyrinth

router = APIRouter()
robot_lab = labyrinth.start()
RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
RUTA_MAPA = RAIZ_PROYECTO / "map.json"

# --- MODELOS DE DATOS ---
class DatosRaspberry(BaseModel):
    device_id: str
    temperatura: float
    humedad: float

class DatosInteraccion(BaseModel):
    tipo: str 

class DatosPosicion(BaseModel):
    pos: list
    dir: str

# --- HELPER AUTOMÁTICO (Escribe el mapa y avisa a la Web en tiempo real) ---
async def guardar_y_notificar_cambio(forzar_render_completo: bool = False):
    """Guarda el estado actual en el JSON y le avisa por WS a la web para que pinte."""
    try:
        # 1. Guardar en disco
        mapa_json_str = robot_lab.toJSON()
        with open(RUTA_MAPA, "w", encoding="utf-8") as f:
            f.write(mapa_json_str)
        
        # 2. Preparar el paquete de telemetría para el WebSocket
        payload = json.dumps({
            "tempPos": robot_lab.currentPos,
            "tempDir": robot_lab.currentDir,
            "update_map": forzar_render_completo  # Le dice al JS si debe re-consultar nodos y POIs
        })
        
        # 3. Escupir los datos secuencialmente a los navegadores abiertos
        for cliente in list(clientes_web):
            try:
                await cliente.send_text(payload)
            except Exception:
                if cliente in clientes_web:
                    clientes_web.remove(cliente)
    except Exception as e:
        print(f"❌ Error en el broadcast de telemetría: {e}")

# --- ENDPOINTS ---

@router.post("/raspberry")
async def obtener_archivo(datos: DatosRaspberry):
    try:
        print(f"Datos recibidos de {datos.device_id}: Temp={datos.temperatura}°C")
        ruta_absoluta = RAIZ_PROYECTO / "archivo.txt"
        with open(ruta_absoluta, "r", encoding="utf-8") as f:
            return {"status": "Datos guardados", "contenido_archivo": f.read()}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"archivo.txt no encontrado en {ruta_absoluta}")

@router.post("/raspberry/next_route")
async def get_next_route():
    try: 
        destination_type, final_commands = labyrinth.skipImage(robot_lab)
        
        # ARREGLADO: Ahora sí guarda y actualiza la web al saltar imágenes
        await guardar_y_notificar_cambio(forzar_render_completo=True)
        
        return {"status": "success", "destination_type": destination_type, "commands": final_commands}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/raspberry/analyze")
async def trigger_analysis(cenital_img: UploadFile = File(...), resized_img: UploadFile = File(...)):
    try:
        cenital_bytes = await cenital_img.read()
        resized_bytes = await resized_img.read()
        
        img_cenital = cv2.imdecode(np.frombuffer(cenital_bytes, np.uint8), cv2.IMREAD_COLOR)
        img_resized = cv2.imdecode(np.frombuffer(resized_bytes, np.uint8), cv2.IMREAD_COLOR)
        
        if img_cenital is None or img_resized is None:
            raise ValueError("Imágenes corruptas.")

        destination_type, final_commands = labyrinth.analyze(robot_lab, img_cenital, img_resized)
        
        # Guarda los nuevos nodos detectados y obliga a la web a recargar estructuras
        await guardar_y_notificar_cambio(forzar_render_completo=True)
        
        return {"status": "success", "destination_type": destination_type, "commands": final_commands}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
@router.post("/raspberry/reset")
async def reset_labyrinth():
    global robot_lab 
    try:
        robot_lab = labyrinth.start()
        await guardar_y_notificar_cambio(forzar_render_completo=True)
        return {"status": "success", "message": "Map wiped."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/raspberry/interactuar")
async def interactuar_objeto(datos: DatosInteraccion):
    try:
        if datos.tipo == 'K': robot_lab.grabKey()
        elif datos.tipo == 'D': robot_lab.unlockDoor()
        elif datos.tipo == '?': robot_lab.scanQR()
        else: raise ValueError("Tipo inválido.")
            
        await guardar_y_notificar_cambio(forzar_render_completo=True)
        return {"status": "success", "message": f"Interactuado con {datos.tipo}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/raspberry/update_position")
async def update_position(datos: DatosPosicion):
    try:
        robot_lab.currentPos = tuple(datos.pos)
        robot_lab.currentDir = datos.dir
        robot_lab.currentNode = robot_lab.map[tuple(datos.pos)]
        
        # Es un simple movimiento de casilla: guardamos y movemos la flecha en la web 
        # sin necesidad de obligar al JS a descargar todo el mapa JSON de nuevo
        await guardar_y_notificar_cambio(forzar_render_completo=False)
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))