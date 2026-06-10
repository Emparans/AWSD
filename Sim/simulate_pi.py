import requests
from pathlib import Path
import cv2
import numpy as np
import time
import json
import threading
import websocket
import base64
import os
import random
import sim
import math

# URL pública de tu FastAPI en la VM
SERVER_URL = "http://34.0.201.131:8080/raspberry"
WS_VIDEO_URL = "ws://34.0.201.131:8080/control/video_stream"

distancesByNTiles = { 1 : 46, 2 : 95}

imageForProcessingName = "proc"
outputCameraRes = (820, 616)

# Estado de telemetría física del Robot
tempDir = 'r'
tempPos = (0, 0)
lastTurn = 'X'

def esperarPasos(tiempo):
    pasos = int(tiempo / 0.05)
    for _ in range(pasos):
        sim.simxSynchronousTrigger(clientID)

def aplicarVelocidades(vel_izq, vel_der):
    sim.simxSetJointTargetVelocity(clientID, ruedaIzquierda, vel_izq, sim.simx_opmode_oneshot)
    sim.simxSetJointTargetVelocity(clientID, ruedaDerecha,   vel_der, sim.simx_opmode_oneshot)

def frenar():
    aplicarVelocidades(0, 0)

def girar(v_angular, grados):
    radio_rueda = 0.04
    L = 0.185
    v_angular_abs = abs(v_angular)
    grados_abs = abs(grados)
    radianes_giro = math.radians(grados_abs)
    distancia_rueda = radianes_giro * (L / 2)
    v_lineal = v_angular_abs * radio_rueda
    t = distancia_rueda / v_lineal
    
    if grados > 0: # Antihorario (Izquierda)
        vel_izq = -v_angular_abs
        vel_der = v_angular_abs
    else:          # Horario (Derecha)
        vel_izq = v_angular_abs
        vel_der = -v_angular_abs

    aplicarVelocidades(vel_izq, vel_der)
    esperarPasos(t) 
    frenar()

def obtener_imagen_simulador():
    """Captura el frame actual del Vision_sensor de CoppeliaSim y lo adapta a OpenCV (BGR)."""
    retCode, resolution, image = sim.simxGetVisionSensorImage(clientID, camara, 0, sim.simx_opmode_blocking)
    print("A")
    img = np.array(image, dtype=np.float32)
    img = img.astype(np.uint8)  # Convierte a uint8
    img.resize(resolution[1], resolution[0], 3)
    img = cv2.flip(img, 0)
    print("O")
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    return img

def avanzar(velocidad, tiempo):
    v = velocidad
    sim.simxSetJointTargetVelocity(clientID, ruedaIzquierda, v, sim.simx_opmode_blocking)
    sim.simxSetJointTargetVelocity(clientID, ruedaDerecha,   v, sim.simx_opmode_blocking)
    esperarPasos(tiempo)
    sim.simxSetJointTargetVelocity(clientID, ruedaIzquierda, 0, sim.simx_opmode_blocking)
    sim.simxSetJointTargetVelocity(clientID, ruedaDerecha,   0, sim.simx_opmode_blocking)

def controlar_electroiman(estado):
    sim.simxSetIntegerSignal(clientID, "estado_iman", estado, sim.simx_opmode_blocking)

def pillarLlave():
    controlar_electroiman(1)
    avanzar(1, 1)
    avanzar(-1, 1)

def abrirPuerta():
    turnRight()
    controlar_electroiman(1)
    turnLeft()

def generate_mapping_sources(img):
    """Genera la homografía en blanco y negro para el análisis del mapa."""
    outputXSize = 800
    latRate = 1/4 
    nTilesInVArea = 4.5
    latMargin = outputXSize * latRate / 2
    outputYSize = int((outputXSize - (2 * latMargin)) * nTilesInVArea)
    WIDTH, HEIGHT = outputXSize, outputYSize
    
    if img is None:
        print("Error: Imagen no recibida correctamente.")
        return None, None

    Base_W, Base_H = 3280, 2464
    h, w = img.shape[:2]
    scale_x, scale_y = w / Base_W, h / Base_H

    pts_src = np.array([[600, 2460], [2792, 2460], [1920, 944], [1400, 944]], dtype=np.float32)

    pts_src[:, 0] *= scale_x  
    pts_src[:, 1] *= scale_y  

    pts_dst = np.array([[latMargin, HEIGHT], [WIDTH - latMargin, HEIGHT], [WIDTH - latMargin, 0], [latMargin, 0]], dtype=np.float32)
    H = cv2.getPerspectiveTransform(pts_src, pts_dst)
    
    processed_orig = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower_brown = np.array([0, 0, 0])
    upper_brown = np.array([102,255,255])
    mask_orig = cv2.inRange(processed_orig, lower_brown, upper_brown)
    
    mask_temp = cv2.warpPerspective(mask_orig, H, (WIDTH, HEIGHT), borderValue=0)
    kernel = np.ones((9,9), np.uint8)
    mask_temp = cv2.morphologyEx(mask_temp, cv2.MORPH_OPEN, kernel)
    mask_temp = cv2.morphologyEx(mask_temp, cv2.MORPH_CLOSE, kernel)

    bottom_30 = int(HEIGHT * 0.7)
    edges = cv2.Canny(mask_temp[bottom_30:, :], 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=40, minLineLength=40, maxLineGap=10)
    
    angles = []
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if y2 > y1: x1, y1, x2, y2 = x2, y2, x1, y1
            dx, dy = x2 - x1, y1 - y2
            if dx != 0 or dy != 0:
                tilt = 90.0 - np.degrees(np.arctan2(dy, dx))
                if -5 < tilt < 5: angles.append(tilt)

    best_tilt = np.median(angles) if angles else 0
        
    bottom_15 = int(HEIGHT * 0.85)
    col_sums = np.mean(mask_temp[bottom_15:, :], axis=0)
    is_wall = col_sums > (255 * 0.3)
    mid_x = WIDTH // 2
    
    left_wall_x, left_wall_found = 0, False
    for x in range(mid_x, -1, -1):
        if is_wall[x]: left_wall_x, left_wall_found = x, True; break
            
    right_wall_x, right_wall_found = WIDTH - 1, False
    for x in range(mid_x, WIDTH):
        if is_wall[x]: right_wall_x, right_wall_found = x, True; break

    shift_x = 0
    if left_wall_found and right_wall_found:
        shift_x = mid_x - ((left_wall_x + right_wall_x) // 2)
    elif left_wall_found:
        shift_x = int(latMargin) - left_wall_x
    elif right_wall_found:
        shift_x = int(WIDTH - latMargin) - right_wall_x
    
    M_rot = cv2.getRotationMatrix2D((WIDTH // 2, HEIGHT), best_tilt, 1.0)
    H_final = np.vstack([M_rot, [0, 0, 1]])
    H_final = np.vstack([[[1, 0, shift_x], [0, 1, 0]], [0, 0, 1]]) @ H_final @ H
    
    mask_final = cv2.warpPerspective(mask_orig, H_final, (WIDTH, HEIGHT), borderValue=0)
    mask_final = cv2.morphologyEx(mask_final, cv2.MORPH_CLOSE, kernel)
    
    print("INFO: Procesamiento morfológico terminado. Dibujando puntos...")

    lado = 51
    mitad = lado // 2
    color_azul = (255, 0, 0) # Azul puro en BGR

    try:
        from pathlib import Path
        directorio = Path(__file__).parent
    except NameError:
        # Si __file__ falla (ej. estás en Jupyter/Colab), usamos la carpeta actual
        import os
        directorio = os.getcwd()
    except Exception as e:
        print(f"Error inesperado con la ruta: {e}")
        directorio = ""

    img_original_dibujada = img.copy()
    
    # pts_src ya tiene las coordenadas ajustadas a la escala de la imagen original
    for (x, y) in pts_src:
        x, y = int(x), int(y)
        pt1 = (x - mitad, y - mitad)
        pt2 = (x + mitad, y + mitad)
        cv2.rectangle(img_original_dibujada, pt1, pt2, color_azul, thickness=-1)

    # Usamos os.path.join o el operador / de Path de forma segura
    ruta_salida = f"{directorio}/org_dotted.jpg"

    # 3. Exportar y verificar éxito
    exito = cv2.imwrite(ruta_salida, img_original_dibujada)
    
    if exito:
        print(f"✅ ÉXITO TOTAL: Imagen guardada en:\n -> {ruta_salida}")
    else:
        print(f"❌ ERROR CRÍTICO: cv2.imwrite falló. Comprueba que tienes permisos de escritura en:\n -> {ruta_salida}")

    # 1. Convertir la máscara a 3 canales para poder dibujar en rojo
    mask_color = cv2.cvtColor(mask_final, cv2.COLOR_GRAY2BGR)

    pts_src_formateados = np.array([pts_src], dtype=np.float32)
    esquinas_finales = cv2.perspectiveTransform(pts_src_formateados, H_final)[0]

    for (x, y) in esquinas_finales:
        x, y = int(x), int(y) # Tienen que ser enteros para poder dibujar
        pt1 = (x - mitad, y - mitad)
        pt2 = (x + mitad, y + mitad)
        cv2.rectangle(mask_color, pt1, pt2, color_azul, thickness=-1)

        interpretationSpots = np.array([
    #MIDDLE
    [400, 2660],
    [400, 2640],
    [400, 2300],
    [400, 2100],
    [400, 1700],
    [400, 1500],
    [400, 1100],
    [400,  900],
    [400,  500],
    [400,  300],

    #LEFT
    [50, 2630],
    [50, 2065],
    [50, 1450],
    [50,  815],
    [50,  180],

    #RIGHT
    [760, 2630],
    [760, 2065],
    [760, 1450],
    [760,  815],
    [760,  180]], 
    dtype=np.int32)

    color_rojo = (0, 0, 255) # Ahora sí será rojo puro
    
    for (x, y) in interpretationSpots:
        pt1 = (x - mitad, y - mitad)
        pt2 = (x + mitad, y + mitad)
        # OJO: Dibujamos sobre mask_color, no sobre mask_final
        cv2.rectangle(mask_color, pt1, pt2, color_rojo, thickness=-1)

    print("INFO: Puntos dibujados. Preparando exportación...")

    # Usamos os.path.join o el operador / de Path de forma segura
    ruta_salida = f"{directorio}/img_dotted.jpg"

    # 3. Exportar y verificar éxito
    exito = cv2.imwrite(ruta_salida, mask_color)
    
    if exito:
        print(f"✅ ÉXITO TOTAL: Imagen guardada en:\n -> {ruta_salida}")
    else:
        print(f"❌ ERROR CRÍTICO: cv2.imwrite falló. Comprueba que tienes permisos de escritura en:\n -> {ruta_salida}")

    return mask_final

def moveForward(nTiles):
    global tempPos, lastTurn
    if nTiles == 0: return
    
    additions = {'u': (0, 1), 'r': (1, 0), 'd': (0, -1), 'l': (-1, 0)}
    addition = additions.get(tempDir, (0, 0))

    v_angular = 1
    v_lineal = v_angular * 0.04
    t = 0.25 / v_lineal
    aplicarVelocidades(v_angular, v_angular)

    for _ in range(nTiles):
        esperarPasos(t)
        tempPos = (tempPos[0] + addition[0], tempPos[1] + addition[1])
        sync_position_with_server()
    
    frenar()
    lastTurn = 'X'
    time.sleep(0.5)

def turnLeft():
    global tempDir, lastTurn
    trans = {'u': 'l', 'r': 'u', 'd': 'r', 'l': 'd'}
    tempDir = trans.get(tempDir, tempDir)
    sync_position_with_server()
    
    girar(1, 90)
        
    lastTurn = 'l'
    time.sleep(0.5)

def turnRight():
    global tempDir, lastTurn
    trans = {'u': 'r', 'r': 'd', 'd': 'l', 'l': 'u'}
    tempDir = trans.get(tempDir, tempDir)
    sync_position_with_server()
    
    girar(1, -90) # Lógica de Coppelia (grados < 0 -> Derecha)

    lastTurn = 'r'
    time.sleep(0.5)

def turnBack():
    global tempDir, lastTurn
    trans = {'u': 'd', 'r': 'l', 'd': 'u', 'l': 'r'}
    tempDir = trans.get(tempDir, tempDir)
    sync_position_with_server()
    
    girar(1, 180)
        
    lastTurn = 'r'
    time.sleep(0.5)

# --- Peticiones de Análisis a la VM ---
def sync_position_with_server():
    try:
        requests.post(f"{SERVER_URL}/update_position", json={"pos": list(tempPos), "dir": tempDir}, timeout=2)
    except requests.exceptions.RequestException: pass

def check_robot_pause():
    try:
        res = requests.get(f"{SERVER_URL}/estado_pausa", timeout=2)
        if res.status_code == 200:
            return res.json().get('pausa', False)
    except requests.exceptions.RequestException:
        pass
    return False

def send_robot_step(homography, resized):
    print("Enviando imágenes de análisis a la VM...")
    try:
        _, cenital_buf = cv2.imencode('.jpg', homography)
        _, resized_buf = cv2.imencode('.jpg', resized)
        
        files = {
            "cenital_img": (f"{imageForProcessingName}_cenitalBW.jpg", cenital_buf.tobytes(), "image/jpeg"),
            "resized_img": (f"{imageForProcessingName}_resized.jpg", resized_buf.tobytes(), "image/jpeg")
        }
        res = requests.post(f"{SERVER_URL}/analyze", files=files, data={"img_name": imageForProcessingName})
        if res.status_code == 200:
            data = res.json()
            return data.get('destination_type'), data.get('commands', [])
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión analizando paso: {e}")
    return None, None

def skip_robot_step():
    print("Saltando paso (Cálculo remoto de ruta)...")
    try:
        res = requests.post(f"{SERVER_URL}/next_route")
        if res.status_code == 200:
            data = res.json()
            return data.get('destination_type'), data.get('commands', [])
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión saltando paso: {e}")
    return None, None

def send_reset_command():
    global tempPos, tempDir
    tempDir, tempPos = 'r', (0, 0)
    print("Enviando comando de reinicio a la VM...")
    try:
        res = requests.post(f"{SERVER_URL}/reset")
        if res.status_code == 200:
            print(f"➡ Servidor reiniciado: {res.json().get('message')}")
    except requests.exceptions.RequestException:
        print("❌ Imposible conectar con FastAPI para realizar Reset.")

def executeCommands(commands):
    if not commands: return
    for cmd in commands:
        action, steps = cmd[0], int(cmd[1])
        if action == 'r': turnRight()
        elif action == 'l': turnLeft()
        elif action == 'b': turnBack()
        moveForward(steps)

# --- Bucle de ejecución principal ---
def robot_loop():
    estado_actual = "ESCANEO" 
    siguiente_estado = None
    dest_type, commands = None, []
    image_idx = 0
    qr_idx = 0
    en_pausa_notificada = False
    
    while True:
        if estado_actual == "PAUSA":
            if check_robot_pause():
                if not en_pausa_notificada:
                    print("⏸️ Robot en PAUSA por orden del servidor. Esperando luz verde...")
                    en_pausa_notificada = True
                time.sleep(1.5)
                continue
            else:
                if en_pausa_notificada:
                    print("▶️ Pausa terminada. Reanudando operaciones...")
                    en_pausa_notificada = False
                estado_actual = siguiente_estado
                continue
        if estado_actual == "ESCANEO":
            if estado_actual == "ESCANEO":
                print("📸 Capturando frame en tiempo real desde CoppeliaSim...")
                frame_bgr = obtener_imagen_simulador()
                
                homography = generate_mapping_sources(frame_bgr)
                if homography is None:
                    time.sleep(1); continue
                    
                dest_type, commands = send_robot_step(homography, frame_bgr)
                if dest_type is None:
                    time.sleep(2); continue
                    
                image_idx += 1
                siguiente_estado = "MOVIMIENTO"
                estado_actual = "PAUSA"

        elif estado_actual == "SALTO_ESCANEO":
            dest_type, commands = skip_robot_step()
            if dest_type is None: time.sleep(2); continue
            siguiente_estado = "MOVIMIENTO"
            estado_actual = "PAUSA"

        elif estado_actual == "MOVIMIENTO":
            if commands:
                print(f"Ejecutando ruta hacia '{dest_type}'. Comandos: {commands}")
                executeCommands(commands)
            siguiente_estado = "INTERACCION"
            estado_actual = "PAUSA"

        elif estado_actual == "INTERACCION":
            if dest_type == 'X' and not commands:
                print("🏁 Laberinto completado o sin salidas."); break
                
            elif dest_type == 'D':
                print(f"Acción en casilla: Interactuando con la puerta...")

                abrirPuerta()

                try:
                    requests.post(f"{SERVER_URL}/interactuar", json={"tipo": 'D'})
                except requests.exceptions.RequestException: pass
                time.sleep(2)
                estado_actual = "ESCANEO"

            elif dest_type == 'K':
                print(f"Acción en casilla: Interactuando con la llave...")

                pillarLlave()
                    
                try:
                    requests.post(f"{SERVER_URL}/interactuar", json={"tipo": 'K'})
                except requests.exceptions.RequestException: pass
                time.sleep(2)
                estado_actual = "SALTO_ESCANEO"


            elif dest_type == '?':
                print("❓ Inspeccionando interrogante (QR) en el simulador...")

                frame = obtener_imagen_simulador()

                frame_pequeno = cv2.resize(frame, (820, 616))
                success, buffer = cv2.imencode('.jpg', frame_pequeno, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
                
                if success:
                    files = {"file": ("qr.jpg", buffer.tobytes(), "image/jpeg")}
                    try:
                        # Mandamos la imagen a la API de control
                        res = requests.post("http://34.0.201.131:8080/control/leer-qr", files=files)
                        if res.status_code == 200:
                            print("✅ QR enviado. Esperando a que el usuario responda por voz...")
                    except Exception as e:
                        print("❌ Error enviando QR:", e)
                
                # 2. BUCLE DE ESPERA (POLLING)
                interaccion_terminada = False
                while not interaccion_terminada:
                    try:
                        # Preguntamos al servidor si el pipeline ya terminó
                        estado_res = requests.get("http://34.0.201.131:8080/control/estado-interaccion", timeout=2)
                        if estado_res.status_code == 200:
                            interaccion_terminada = estado_res.json().get("completada", False)
                    except:
                        pass
                    
                    if not interaccion_terminada:
                        time.sleep(2) 
                
                print("🎙️ Respuesta procesada por Gemini. ¡El robot continúa!")
                
                try:
                    requests.post(f"{SERVER_URL}/interactuar", json={"tipo": "?"})
                except requests.exceptions.RequestException: pass
                
                qr_idx += 1

                estado_actual = "SALTO_ESCANEO"
                
            elif dest_type == 'X':
                estado_actual = "ESCANEO"
                
        time.sleep(0.1)

if __name__ == "__main__":
    try:
        TIEMPO_AVANCE_CASILLA = 6.25 # Segundos que tarda en avanzar 1 casilla entera
        TIEMPO_GIRO = 3.6324665057131984     # Segundos que tarda en rotar 90 grados
        POTENCIA_MOTORES_AVANCE = 0.3
        POTENCIA_MOTORES_GIRO = 0.3
    
        print("[💻] INICIANDO EN MODO SIMULACIÓN (PC)...")
        # Conexión a CoppeliaSim
        sim.simxFinish(-1)
        clientID = sim.simxStart('127.0.0.1', 19999, True, True, 2000, 5)
        if clientID == 0:
            print("✅ Conectado a CoppeliaSim en el puerto 19999")
        else:
            print("❌ No se pudo conectar a CoppeliaSim")
            os._exit(1)
        
        # Modo síncrono
        sim.simxSynchronous(clientID, True)
        sim.simxStartSimulation(clientID, sim.simx_opmode_blocking)

        # Obtener handles
        _, camara = sim.simxGetObjectHandle(clientID, 'Vision_sensor', sim.simx_opmode_blocking)
        _, ruedaDerecha = sim.simxGetObjectHandle(clientID, 'RuedaR', sim.simx_opmode_blocking)
        _, ruedaIzquierda = sim.simxGetObjectHandle(clientID, 'RuedaL', sim.simx_opmode_blocking)
        _, ultrasonidoDerecha = sim.simxGetObjectHandle(clientID, 'SensorR', sim.simx_opmode_blocking)
        _, ultrasonidoIzquierda = sim.simxGetObjectHandle(clientID, 'SensorL', sim.simx_opmode_blocking)
        _, ultrasonidoDelante = sim.simxGetObjectHandle(clientID, 'SensorD', sim.simx_opmode_blocking)
        _, ultrasonidoAtras = sim.simxGetObjectHandle(clientID, 'SensorA', sim.simx_opmode_blocking)

        # Mapeo de sensores para la lógica de paredes
        SENSORES_SIM = {
            "Delantero": ultrasonidoDelante,
            "Izquierda": ultrasonidoIzquierda,
            "Derecha": ultrasonidoDerecha,
            "Trasero": ultrasonidoAtras
        }
        
        send_reset_command()
        robot_loop()

    except KeyboardInterrupt:
        print("\n[!] Simulación detenida manualmente.")