import requests
from pathlib import Path
import cv2
import numpy as np
import time
import websocket

import math
import time
from gpiozero import DistanceSensor, OutputDevice, PWMOutputDevice
from picamera2 import Picamera2

SERVER_URL = "http://34.0.201.131:8080/raspberry"
WS_VIDEO_URL = "ws://34.0.201.131:8080/control/video_stream"

imageForProcessingName = "proc"
outputCameraRes = (820, 616)
real = Path(__file__).parent / "real"

tempDir = 'r'
tempPos = (0, 0)
lastTurn = 'X'

llaveHeld = 1

def sacar_foto():
    print("Activando sensor de cámara...")
    try:
        picam.start()
        time.sleep(1.2)  # Tiempo para que el sensor regule la luz ambiental
        
        unfiltered_array = picam.capture_array("main")
        
        picam.stop()
        print("Sensor en reposo. Procesando bytes...")
                
                
        scaled_array = unfiltered_array[::4, ::4]
        return scaled_array
                
    except Exception as e:
        print(f"Error en el ciclo de captura: {e}")
        try: picam.stop()
        except: pass
    time.sleep(1)

def obtener_distancia(nombre):
    mapeo_sensores = {
        "Izquierda": "Derecha",
        "Derecha": "Izquierda"
    }
    sensor_key = mapeo_sensores.get(nombre, nombre)
    s = sensores[sensor_key]
    distancia = s.distance * 100 if s.distance is not None else 999.0
    
    if nombre == "Derecha":
        distancia += 1
    return distancia

def configurar_direcciones(a1, a2, b1, b2):
    mA_in1.value, mA_in2.value = a1, a2
    mB_in1.value, mB_in2.value = b1, b2

def detener_motores():
    mA_pwm.value = mB_pwm.value = 0.0
    configurar_direcciones(0, 0, 0, 0)


def girar_suave(grados=90, direccion="derecha", tiempo_estimado=0.45):
    global llaveHeld
    tiempo_estimado = tiempo_estimado * max((llaveHeld / 1.1),1)
    print(f"Giro hacia la {direccion}...")
    dir_giro = (1, 0, 0, 1) if direccion == "derecha" else (0, 1, 1, 0)
    dir_atras = (0, 1, 1, 0) if direccion == "derecha" else (1, 0, 0, 1)

    sensores_prioridad = ["Inferior", "Izquierda", "Derecha", "Delantero"] 
    distancias = {sensor: obtener_distancia(sensor) for sensor in sensores_prioridad}
    sensorIdeal = "Inferior"

    for sensor, valor in distancias.items():
        print(f"-{sensor}: {valor:.2f} cm")

    if(tiempo_estimado < 0.5):
        if(direccion=="derecha"):
            if distancias["Izquierda"] < 10:
                if(distancias["Delantero"] < distancias["Izquierda"]):
                    sensorIdeal = "Derecha"
                else:
                    sensorIdeal = "Inferior"
            else:
                sensorIdeal = "Derecha"

        elif(direccion=="izquierda"):
            if distancias["Derecha"] < 10:
                if(distancias["Delantero"] < distancias["Derecha"]):
                    sensorIdeal = "Izquierda"
                else:
                    sensorIdeal = "Inferior"
            else:
                sensorIdeal = "Izquierda"
    
    print(f"Sensor Ideal: {sensorIdeal}")

    #Giro grueso
    configurar_direcciones(*dir_giro)
    t0 = time.time()
    while (time.time() - t0) < tiempo_estimado:
        progreso = (time.time() - t0) / tiempo_estimado
        mA_pwm.value = mB_pwm.value = max(0.0, min(1.0, 0.15 + 0.55 * math.sin(progreso * math.pi)))
        time.sleep(0.02)
    detener_motores()
    time.sleep(0.3)

    #Barrido
    configurar_direcciones(*dir_atras) 
    mA_pwm.value = mB_pwm.value = 0.30 
    time.sleep(0.40)                    
    detener_motores()
    time.sleep(0.15)
    
    configurar_direcciones(*dir_giro) 
    mA_pwm.value = mB_pwm.value = 0.16 * max((llaveHeld / 1.7),1)
    dist_minima = obtener_distancia(sensorIdeal)
    inicio_escaneo = time.time()

    while True:
        dist_actual = obtener_distancia(sensorIdeal)
        if dist_actual == 999.0: continue
        if dist_actual < dist_minima: dist_minima = dist_actual
        if (time.time() - inicio_escaneo) > 1.45 and dist_actual > (dist_minima + 0.4): break
        time.sleep(0.01)

    #Corrección final
    configurar_direcciones(*dir_atras) 
    mA_pwm.value = mB_pwm.value = 0.55  
    time.sleep(0.08 * max((llaveHeld / 1.3),1))                    
    detener_motores()
    time.sleep(0.2)

def avanzar_corrigiendo(distancia_cm=56, potenciaMax = 0.45, target_frontal=None):
    global llaveHeld
    distancia_cm = distancia_cm * max((llaveHeld / 1.5),1)
    potenciaMax = potenciaMax * max((llaveHeld / 1.5),1)
    tiempo_estimado = (abs(distancia_cm) * 1.5) / 50.0
    print(f"[~] Avanzando {distancia_cm}cm...")
    Kp, Kd = 0.008, 0.008
    UMBRAL_PARED, TARGET_CERCA, POTENCIA_FINA = 15.0, 5.0, 0.15 * llaveHeld
    dist_izq_ant = dist_der_ant = None

    #Avance grueso
    if distancia_cm >= 0:
        configurar_direcciones(1, 0, 1, 0)
    else:
        configurar_direcciones(0, 1, 0, 1)
        
    t0 = time.time()
    while (time.time() - t0) < tiempo_estimado:
        progreso = (time.time() - t0) / tiempo_estimado
        potencia = max(0.0, min(1.0, 0.15 + potenciaMax * math.sin(progreso * math.pi)))
        cambio_izq = cambio_der = correccion = 0.0
        
        dist_izq, dist_der = obtener_distancia("Izquierda"), obtener_distancia("Derecha")
        if dist_izq < UMBRAL_PARED:
            if dist_izq_ant is not None and dist_izq_ant < UMBRAL_PARED: cambio_izq = dist_izq - dist_izq_ant  
            correccion += ((dist_izq - TARGET_CERCA) * Kp) + (cambio_izq * Kd)
            dist_izq_ant = dist_izq
        else: dist_izq_ant = None 

        if dist_der < UMBRAL_PARED:
            if dist_der_ant is not None and dist_der_ant < UMBRAL_PARED: cambio_der = dist_der - dist_der_ant  
            correccion -= ((dist_der - TARGET_CERCA) * Kp) + (cambio_der * Kd)
            dist_der_ant = dist_der
        else: dist_der_ant = None

        if distancia_cm < 0:
            correccion = -correccion

        mA_pwm.value = max(0.12, min(0.95, potencia - (correccion * max((llaveHeld / 1.5),1) - 0.01)))
        mB_pwm.value = max(0.12, min(0.95, potencia + (correccion * max((llaveHeld / 1.5),1))))
        time.sleep(0.02)

    detener_motores()
    time.sleep(0.2)

    #Ajuste longitudinal fino
    dist_del, dist_tras = obtener_distancia("Delantero"), obtener_distancia("Inferior")
    sensor_elegido = "Delantero" if dist_del < dist_tras else "Inferior"
    dist_inicial = dist_del if dist_del < dist_tras else dist_tras

    if dist_inicial > 45.0:
        detener_motores()
        return

    if target_frontal is not None:
        target = target_frontal
    else:
        target = 5.0 if dist_inicial < 17.5 else 30.0
        
    dist_izq_ant = dist_der_ant = None
    target_izq = obtener_distancia("Izquierda") if obtener_distancia("Izquierda") < UMBRAL_PARED else TARGET_CERCA
    target_der = obtener_distancia("Derecha") if obtener_distancia("Derecha") < UMBRAL_PARED else TARGET_CERCA

    while True:
        dist_actual = obtener_distancia(sensor_elegido)
        error = dist_actual - target
        if abs(error) < 0.5: break

        moviendo_adelante = True
        if sensor_elegido == "Delantero":
            if error > 0: configurar_direcciones(1, 0, 1, 0)
            else: configurar_direcciones(0, 1, 0, 1); moviendo_adelante = False
        else: 
            if error > 0: configurar_direcciones(0, 1, 0, 1); moviendo_adelante = False
            else: configurar_direcciones(1, 0, 1, 0)

        dist_izq, dist_der = obtener_distancia("Izquierda"), obtener_distancia("Derecha")
        correccion_lateral = 0.0

        if dist_izq < UMBRAL_PARED:
            cambio_izq = (dist_izq - dist_izq_ant) if dist_izq_ant is not None else 0.0
            correccion_lateral += (dist_izq - target_izq) * Kp + (cambio_izq * Kd)
            dist_izq_ant = dist_izq
            
        if dist_der < UMBRAL_PARED:
            cambio_der = (dist_der - dist_der_ant) if dist_der_ant is not None else 0.0
            correccion_lateral -= (dist_der - target_der) * Kp + (cambio_der * Kd)
            dist_der_ant = dist_der

        if not moviendo_adelante: correccion_lateral = -correccion_lateral

        mA_pwm.value = max(0.10, min(0.25, POTENCIA_FINA - correccion_lateral))
        mB_pwm.value = max(0.10, min(0.25, POTENCIA_FINA + correccion_lateral))
        time.sleep(0.01)

    detener_motores()
    time.sleep(0.2)
    
imageID = 0
def generate_mapping_sources(img):
    global imageID
    """Genera la homografía en blanco y negro para el análisis del mapa."""
    outputXSize = 800
    latRate = 1/4 
    nTilesInVArea = 4.5
    latMargin = outputXSize * latRate / 2
    outputYSize = int((outputXSize - (2 * latMargin)) * nTilesInVArea)
    WIDTH, HEIGHT = outputXSize, outputYSize
    
    if img is None:
        print("Error: Imagen no recibida correctamente.")
        return None

    try:
        from pathlib import Path
        directorio = Path(__file__).parent
    except NameError:
        import os
        directorio = os.getcwd()
    except Exception as e:
        print(f"Error inesperado con la ruta: {e}")
        directorio = ""

    ruta_salida2 = f"{directorio}/normal.jpg"

    # 3. Exportar y verificar éxito
    exito2 = cv2.imwrite(ruta_salida2, img)

    Base_W, Base_H = 3280, 2464
    h, w = img.shape[:2]
    scale_x, scale_y = w / Base_W, h / Base_H

    pts_src = np.array([[68, 2463], [3182, 2463], [1820, 880], [1332, 880]], dtype=np.float32)
    pts_src[:, 0] *= scale_x  
    pts_src[:, 1] *= scale_y  

    pts_dst = np.array([[latMargin, HEIGHT], [WIDTH - latMargin, HEIGHT], [WIDTH - latMargin, 0], [latMargin, 0]], dtype=np.float32)
    H = cv2.getPerspectiveTransform(pts_src, pts_dst)
    
    processed_orig = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    if imageID == 6:
        lower_brown = np.array([0, 0, 0])
        upper_brown = np.array([105, 90, 255])
    else:
        
        lower_brown = np.array([0, 0, 0])
        upper_brown = np.array([45, 255, 255])
    imageID += 1


    mask_orig = cv2.inRange(processed_orig, lower_brown, upper_brown)
    
    mask_temp = cv2.warpPerspective(mask_orig, H, (WIDTH, HEIGHT), borderValue=0)
    kernel = np.ones((9,9), np.uint8)
    mask_temp = cv2.morphologyEx(mask_temp, cv2.MORPH_OPEN, kernel)
    mask_temp = cv2.morphologyEx(mask_temp, cv2.MORPH_CLOSE, kernel)

    bottom_30 = int(HEIGHT * 0.7)
    edges = cv2.Canny(mask_temp[bottom_30:, :], 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=80, minLineLength=40, maxLineGap=10)
    
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

    # 1. Convertir la máscara a 3 canales para poder dibujar en rojo
    mask_color = cv2.cvtColor(mask_final, cv2.COLOR_GRAY2BGR)

    interpretationSpots = np.array([
    # MIDDLE
    [400, 2699], [400, 2650], [400, 2500], [400, 2300],
    [400, 1900], [400, 1700], [400, 1300], [400, 1100],
    [400,  700], [400,  500],

    # LEFT
    [75, 2650], [75, 2250], [75, 1700], [75,  1150],
    [75,   600],

    # RIGHT
    [700, 2650], [700, 2250], [700, 1700], [700,  1150],
    [700,   600]
    ], dtype=np.int32)

    lado = 51
    mitad = lado // 2
    color_rojo = (0, 0, 255)
    
    for (x, y) in interpretationSpots:
        pt1 = (x - mitad, y - mitad)
        pt2 = (x + mitad, y + mitad)
        cv2.rectangle(mask_color, pt1, pt2, color_rojo, thickness=-1)

    print("INFO: Puntos dibujados. Preparando exportación...")

    # 2. Sistema a prueba de fallos para la ruta
    try:
        from pathlib import Path
        directorio = Path(__file__).parent
    except NameError:
        import os
        directorio = os.getcwd()
    except Exception as e:
        print(f"Error inesperado con la ruta: {e}")
        directorio = ""

    ruta_salida = f"{directorio}/img_dotted.jpg"

    # 3. Exportar y verificar éxito
    exito = cv2.imwrite(ruta_salida, mask_color)
    
    if exito:
        print(f"ÉXITO TOTAL: Imagen guardada en:\n -> {ruta_salida}")
    else:
        print(f"ERROR CRÍTICO: cv2.imwrite falló. Comprueba que tienes permisos de escritura en:\n -> {ruta_salida}")

    return mask_final

def moveForward(nTiles):
    global tempPos, lastTurn
    if nTiles == 0: return
    
    additions = {'u': (0, 1), 'r': (1, 0), 'd': (0, -1), 'l': (-1, 0)}
    addition = additions.get(tempDir, (0, 0))

    avanzar_corrigiendo(DISTANCIA_CASILLA * nTiles)

    tempPos = (tempPos[0] + addition[0] * nTiles, tempPos[1] + addition[1] * nTiles)
    sync_position_with_server()
        
    lastTurn = 'X'
    time.sleep(0.5)

def turnLeft():
    global tempDir, lastTurn
    trans = {'u': 'l', 'r': 'u', 'd': 'r', 'l': 'd'}
    tempDir = trans.get(tempDir, tempDir)
    sync_position_with_server()
    girar_suave(direccion="izquierda", tiempo_estimado=TIEMPO_GIRO_NORMAL)
    lastTurn = 'l'
    time.sleep(0.5)

def turnRight():
    global tempDir, lastTurn
    trans = {'u': 'r', 'r': 'd', 'd': 'l', 'l': 'u'}
    tempDir = trans.get(tempDir, tempDir)
    sync_position_with_server()
    girar_suave(direccion="derecha", tiempo_estimado=TIEMPO_GIRO_NORMAL)
    lastTurn = 'r'
    time.sleep(0.5)

def turnBack():
    global tempDir
    trans = {'u': 'd', 'r': 'l', 'd': 'u', 'l': 'r'}
    tempDir = trans.get(tempDir, tempDir)
    sync_position_with_server()
    girar_suave(direccion="izquierda", tiempo_estimado=TIEMPO_GIRO_180)
    lastTurn = 'r'
    time.sleep(0.5)


def pickUpKey():
    global llaveHeld
    print("Llave Held")
    llaveHeld = 1.8
    rele.on()
    time.sleep(0.1)
    avanzar_corrigiendo(distancia_cm=20, potenciaMax=0.25)
    time.sleep(0.1)
    avanzar_corrigiendo(distancia_cm=-20, potenciaMax=0.25, target_frontal=10)

def openDoor():
    global llaveHeld
    print("Llave no held")
    girar_suave(direccion="derecha", tiempo_estimado=TIEMPO_GIRO_NORMAL)
    time.sleep(1)
    avanzar_corrigiendo(distancia_cm=15, potenciaMax=0.25)
    time.sleep(0.5)
    llaveHeld = 1
    rele.off()
    time.sleep(0.5)
    avanzar_corrigiendo(distancia_cm=-10, potenciaMax=0.25)
    time.sleep(1)
    girar_suave(direccion="izquierda", tiempo_estimado=TIEMPO_GIRO_NORMAL)

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
        print(f"Error de conexión analizando paso: {e}")
    return None, None

def skip_robot_step():
    print("Saltando paso (Cálculo remoto de ruta)...")
    try:
        res = requests.post(f"{SERVER_URL}/next_route")
        if res.status_code == 200:
            data = res.json()
            return data.get('destination_type'), data.get('commands', [])
    except requests.exceptions.RequestException as e:
        print(f"Error de conexión saltando paso: {e}")
    return None, None

def send_reset_command():
    global tempPos, tempDir
    tempDir, tempPos = 'r', (0, 0)
    print("Enviando comando de reinicio a la VM...")
    try:
        res = requests.post(f"{SERVER_URL}/reset")
        if res.status_code == 200:
            print(f"Servidor reiniciado: {res.json().get('message')}")
    except requests.exceptions.RequestException:
        print("Imposible conectar con FastAPI para realizar Reset.")

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
                    print("Robot en PAUSA por orden del servidor. Esperando luz verde...")
                    en_pausa_notificada = True
                time.sleep(1.5)
                continue
            else:
                if en_pausa_notificada:
                    print("Pausa terminada. Reanudando operaciones...")
                    en_pausa_notificada = False
                estado_actual = siguiente_estado
                continue
        if estado_actual == "ESCANEO":
            frame_bgr = sacar_foto()
            homography = generate_mapping_sources(frame_bgr)
            if homography is None:
                time.sleep(1); continue
                
            dest_type, commands = send_robot_step(homography, frame_bgr)
            if dest_type is None:
                time.sleep(1); continue
                
            image_idx += 1
            siguiente_estado = "MOVIMIENTO"
            estado_actual = "PAUSA"

        elif estado_actual == "SALTO_ESCANEO":
            dest_type, commands = skip_robot_step()
            if dest_type is None: time.sleep(1); continue
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
                print("Laberinto completado o sin salidas."); break
            elif dest_type == 'D':
                print(f"Acción en casilla: Interactuando con la puerta...")
                openDoor()
                try:
                    requests.post(f"{SERVER_URL}/interactuar", json={"tipo": 'D'})
                except requests.exceptions.RequestException: pass
                time.sleep(1)
                estado_actual = "ESCANEO"
            elif dest_type == 'K':
                print(f"Acción en casilla: Interactuando con la llave...")
                pickUpKey()
                try:
                    requests.post(f"{SERVER_URL}/interactuar", json={"tipo": 'K'})
                except requests.exceptions.RequestException: pass
                time.sleep(1)
                estado_actual = "SALTO_ESCANEO"


            elif dest_type == '?':
                print("Inspeccionando interrogante (QR)...")

                frame_pequeno = sacar_foto()
                success, buffer = cv2.imencode('.jpg', frame_pequeno, [int(cv2.IMWRITE_JPEG_QUALITY), 60])

                if success:
                    files = {"file": ("qr.jpg", buffer.tobytes(), "image/jpeg")}
                    try:
                        # Mandamos la imagen a la API de control
                        res = requests.post("http://34.0.201.131:8080/control/leer-qr", files=files)
                        if res.status_code == 200:
                            print("QR enviado. Esperando a que el usuario responda por voz...")
                    except Exception as e:
                        print("Error enviando QR:", e)
                
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
                        # Si no ha terminado, el robot sigue parado sin hacer nada
                        time.sleep(1) 
                
                print("Respuesta procesada por Gemini. ¡El robot continúa!")
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
        DISTANCIA_CASILLA = 56
        TIEMPO_GIRO_NORMAL = 0.5
        TIEMPO_GIRO_180 = 1.1

        print("[+] Conectando WebSocket y configurando Cámara...")
        ws_url = "ws://34.0.201.131:8080/ws/pi"
        try:
            ws = websocket.WebSocket()
            ws.connect(ws_url)
        except Exception as e:
            print(f"Alerta de Red: No se pudo conectar al servidor ({e})")

        picam = Picamera2()
        config = picam.create_still_configuration(main={"size": (3280, 2464)})

        config["main"]["format"] = "RGB888" 
        picam.configure(config)

        # Configuración de Motores y Sensores
        mA_in1, mA_in2, mA_pwm = OutputDevice(20), OutputDevice(16), PWMOutputDevice(12)
        mB_in1, mB_in2, mB_pwm = OutputDevice(6), OutputDevice(19), PWMOutputDevice(13)

        sensores = {
            "Delantero": DistanceSensor(echo=11, trigger=8, max_distance=1.0),
            "Izquierda": DistanceSensor(echo=22, trigger=23, max_distance=1.0),
            "Derecha": DistanceSensor(echo=18, trigger=17, max_distance=1.0),
            "Inferior": DistanceSensor(echo=9, trigger=25, max_distance=1.0),
        }
        rele = OutputDevice(26, active_high=True, initial_value=False)
        
        send_reset_command()
        robot_loop()

    except KeyboardInterrupt:
        print("\n[!] Cancelado por el usuario.")
    finally:
        detener_motores()
        mA_in1.close(); mA_in2.close(); mA_pwm.close()
        mB_in1.close(); mB_in2.close(); mB_pwm.close()
        try: picam.close()
        except: pass
        try: ws.close() 
        except: pass


