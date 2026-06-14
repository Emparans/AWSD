from fastapi import APIRouter, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from pathlib import Path
import cv2
import numpy as np
import json

import state

from .control import clientes_web 

import labyrinth

robot_en_pausa = False

router = APIRouter()

# Ruta on es guarda una còpia del mapa actual (per persistència local)
RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
RUTA_MAPA = RAIZ_PROYECTO / "map.json"

# Models de dades per validar el body de les peticions
class DatosInteraccion(BaseModel):
    tipo: str # 'K' per clau, 'D' per porta, '?' per QR

class DatosPosicion(BaseModel):
    pos: list  # Coordenades [x, y]
    dir: str   # Direcció actual (N, S, E, O)


espectadores = []


# 3. WebSocket para los Navegadores Web
@router.websocket("/ws/viewer")
async def websocket_viewer(websocket: WebSocket):
    await websocket.accept()
    espectadores.append(websocket)
    print(f"Nuevo espectador conectado. Total: {len(espectadores)}")
    try:
        while True:
            # Mantiene la conexión abierta esperando cualquier texto (o ping)
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in espectadores:
            espectadores.remove(websocket)
        print("Espectador desconectado.")


# Funció auxiliar: guarda l'estat del robot en un fitxer JSON i notifica els clients web
async def guardar_y_notificar_cambio(forzar_render_completo: bool = False, reinicioCrono: bool = False):
    """
    Serialitza l'estat actual del robot a JSON, l'escriu al fitxer map.json,
    i envia una notificació via WebSocket a tots els clients web connectats.
    forzar_render_completo: si True, indica al frontend que ha de redibuixar tot el mapa.
    """
    try:
        # Converteix l'objecte state.robot_lab a string JSON
        mapa_json_str = state.robot_lab.toJSON()
        with open(RUTA_MAPA, "w", encoding="utf-8") as f:
            f.write(mapa_json_str)

        # Prepara el missatge per als clients web
        payload = json.dumps({
            "tempPos": state.robot_lab.currentPos, # Posició actual
            "tempDir": state.robot_lab.currentDir, # Direcció actual
            "update_map": forzar_render_completo,   # Si cal refrescar tot el mapa
            "reinicio_crono": reinicioCrono
        })
        
        # Envia a cada client web (còpia per evitar errors en modificar la llista)
        for cliente in list(clientes_web):
            try:
                await cliente.send_text(payload)
            except Exception:
                if cliente in clientes_web:
                    clientes_web.remove(cliente)
    except Exception as e:
        print(f"Error broadcast: {e}")

# ---------- ENDPOINTS PER A LA RASPBERRY PI ----------

@router.get("/raspberry/estado_pausa")
def get_estado_pausa():
    """Retorna si el robot està en pausa. La Raspberry consulta aquest estat periòdicament."""
    return {"pausa": robot_en_pausa}

@router.post("/raspberry/pausar_robot")
def pausar_robot(pausar: bool):
    """Canvia l'estat de pausa. Normalment ho crida la interfície web."""
    global robot_en_pausa
    robot_en_pausa = pausar
    return {"message": f"Robot pausado: {robot_en_pausa}"}

@router.post("/raspberry/next_route")
async def get_next_route():
    """
    Endpoint que la Raspberry crida quan acaba una seqüència de moviments.
    Retorna la següent llista d'ordres sense necessitat d'enviar imatges (només amb l'estat actual).
    Utilitza labyrinth.skipImage() per calcular la ruta basant-se en el mapa ja conegut.
    """
    try: 
        # skipImage retorna el tipus de destinació (ex: 'explorar', 'qr', 'door') i la llista d'ordres
        destination_type, final_commands = labyrinth.skipImage(state.robot_lab)
        
        # Si final_commands és llista buida [], vol dir que el robot ha acabat (laberint complet)
        # Notifica els clients perquè refresquin el mapa
        await guardar_y_notificar_cambio(forzar_render_completo=True)
        
        return {"status": "success", "destination_type": destination_type, "commands": final_commands}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/raspberry/analyze")
async def trigger_analysis(cenital_img: UploadFile = File(...), resized_img: UploadFile = File(...)):
    """
    Endpoint principal per a la navegació autònoma.
    La Raspberry hi envia dues imatges:
      - cenital_img: vista des de dalt (per detectre parets, passadissos)
      - resized_img: imatge redimensionada per a processament ràpid
    El servidor les processa amb OpenCV i la funció labyrinth.analyze() per decidir la següent ruta.
    """    
    try:
        # Llegim els bytes de les imatges enviades
        cenital_bytes = await cenital_img.read()
        resized_bytes = await resized_img.read()
        
        # Convertim els bytes a arrays NumPy i després a imatges OpenCV (BGR)
        img_cenital = cv2.imdecode(np.frombuffer(cenital_bytes, np.uint8), cv2.IMREAD_COLOR)
        img_resized = cv2.imdecode(np.frombuffer(resized_bytes, np.uint8), cv2.IMREAD_COLOR)
        
        if img_cenital is None or img_resized is None:
            raise ValueError("Imágenes corruptas.")

        # La funció labyrinth.analyze retorna el tipus de destinació i la llista d'ordres
        destination_type, final_commands = labyrinth.analyze(state.robot_lab, img_cenital, img_resized)
        # Si final_commands és [] vol dir que ha acabat

        _, buffer = cv2.imencode('.jpg', img_resized)
        bytes_a_enviar = buffer.tobytes()

        for espectador in list(espectadores): # Usamos list() para evitar errores al eliminar elementos en caliente
            try:
                await espectador.send_bytes(bytes_a_enviar)
            except Exception:
                if espectador in espectadores:
                    espectadores.remove(espectador)

        # Notifica els clients del canvi d'estat (mapa actualitzat)
        await guardar_y_notificar_cambio(forzar_render_completo=True)
        
        return {"status": "success", "destination_type": destination_type, "commands": final_commands}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
@router.post("/raspberry/reset")
async def reset_labyrinth():
    """
    Reinicia l'estat del laberint (crea un nou objecte RobotLab des de labyrinth.start()).
    Útil per començar una nova partida sense reiniciar el servidor.
    """
    #global state.robot_lab 
    try:
        state.robot_lab = labyrinth.start()
        await guardar_y_notificar_cambio(forzar_render_completo=True, reinicioCrono = True)
        return {"status": "success", "message": "Map wiped."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/raspberry/interactuar")
async def interactuar_objeto(datos: DatosInteraccion):
    """
    Quan el robot troba un objecte (clau, porta o QR), crida aquest endpoint
    per actualitzar l'estat intern (agafar clau, obrir porta, escanejar QR).
    """
    try:
        if datos.tipo == 'K': state.robot_lab.grabKey()        # Clau
        elif datos.tipo == 'D': state.robot_lab.unlockDoor()   # Porta
        elif datos.tipo == '?': state.robot_lab.scanQR()       # QR
        else: raise ValueError("Tipo inválido.")
            
        await guardar_y_notificar_cambio(forzar_render_completo=True)
        return {"status": "success", "message": f"Interactuado con {datos.tipo}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/raspberry/update_position")
async def update_position(datos: DatosPosicion):
    """
    La Raspberry informa al servidor de la seva nova posició i direcció després de cada moviment.
    Actualitza l'estat global i notifica els clients.
    """
    try:
        # Converteix la llista [x,y] a tupla per a l'estat del robot
        state.robot_lab.currentPos = tuple(datos.pos)
        state.robot_lab.currentDir = datos.dir
        # Actualitza el node actual del mapa
        state.robot_lab.currentNode = state.robot_lab.map[tuple(datos.pos)]
        
        # Notifica els clients (sense forçar render complet, només actualitza posició)
        await guardar_y_notificar_cambio(forzar_render_completo=False)
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))