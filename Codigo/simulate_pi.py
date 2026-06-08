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

MODO_SIMULACION = False

# URL pública de tu FastAPI en la VM
SERVER_URL = "http://34.0.201.131:8080/raspberry"
WS_VIDEO_URL = "ws://34.0.201.131:8080/control/video_stream"

imageForProcessingName = "proc"
outputCameraRes = (820, 616)
real = Path(__file__).parent / "real"

# Estado de telemetría física del Robot
tempDir = 'r'
tempPos = (0, 0)
lastTurn = 'X'

# CAMBIO NUEVO: Evento de sincronización para esperar a la cámara
camara_activa = threading.Event()

if not MODO_SIMULACION:
    from picamera2 import Picamera2
    from gpiozero import OutputDevice, PWMOutputDevice, Device, DistanceSensor
    from gpiozero.pins.pigpio import PiGPIOFactory
    
    Device.pin_factory = PiGPIOFactory()
    picam2 = Picamera2()
else:
    picam2 = None # Placeholder para que no dé error en PC

#Sensor related functions
def leer_distancia_robusta(nombre_sensor, num_muestras=5):
    if MODO_SIMULACION: return 15.0
    
    sensor = SENSORES[nombre_sensor]
    muestras = []
    
    for _ in range(num_muestras):
        dist = sensor.distance * 100
        if dist > 0:
            muestras.append(dist)
        time.sleep(0.1) # Micro-pausa para tomar lecturas distintas
    
    return np.median(muestras) if muestras else -1.0

def evaluar_sensor_aislado(nombre_sensor, num_muestras=5):
    if MODO_SIMULACION: return 15.0, 0.1
    
    sensor = SENSORES[nombre_sensor]
    muestras = []
    
    for _ in range(num_muestras):
        dist = sensor.distance * 100
        if dist > 0:
            muestras.append(dist)
        time.sleep(0.1)
        
    if len(muestras) < 3:
        return 300.0, 999.0 
        
    return np.median(muestras), float(np.var(muestras))

def buscar_mejor_pared():
    resultados = {}
    
    for nombre in SENSORES.keys():
        dist, varianza = evaluar_sensor_aislado(nombre)
        score = dist + (varianza * 5.0)
        
        # Guardamos el score SOLO si la pared está lo suficientemente cerca
        if dist < 40.0:
            resultados[nombre] = score
            print(f"   - {nombre: <10}: Dist {dist:04.1f}cm | Var {varianza:04.2f} -> Score: {score:05.1f}")
            
    if not resultados:
        print("No trustworthy walls around")
        return None
        
    ganador = min(resultados, key=resultados.get)
    
    print(f"Using {ganador} wall as reference (Score ganador: {resultados[ganador]:0.1f})")
    return ganador

# def orientate():
#     ref = buscar_mejor_pared()

#     if not ref:
#         return

#     print(f"\n🧭 Iniciando alineación inteligente con pared: {ref}")
#     power = 0.15
#     spinTime = 0.05
#     max_intentos = 20
#     timeBetweenSteps = 0.25
    
#     ruido_tolerancia = 0.3 

#     dist_inicial = leer_distancia_robusta(ref)
#     print(f"   Distancia inicial: {dist_inicial:0.1f} cm")

#     hardware_girar_derecha(spinTime, power)
#     sleep_preciso_hardware(timeBetweenSteps)
#     dist_prueba = leer_distancia_robusta(ref)

#     if dist_prueba < dist_inicial:
#         print(f"   Prueba derecha ({dist_prueba:0.1f} cm): ¡Mejora! Seguimos a la derecha.")
#         turningDir = 'r'
#         mejor_dist = dist_prueba
#         pasos_desde_mejor = 0
#     else:
#         print(f"   Prueba derecha ({dist_prueba:0.1f} cm): Empeora. Cambiando a izquierda.")
#         turningDir = 'l'
#         hardware_girar_izquierda(spinTime, power)
#         sleep_preciso_hardware(timeBetweenSteps)
#         mejor_dist = dist_inicial
#         pasos_desde_mejor = 0

#     intentos = 0
#     while intentos < max_intentos:
#         if turningDir == 'r':
#             hardware_girar_derecha(spinTime, power)
#         else:
#             hardware_girar_izquierda(spinTime, power)

#         sleep_preciso_hardware(timeBetweenSteps)
#         dist_actual = leer_distancia_robusta(ref)
#         print(f"   Paso {intentos + 1}: {dist_actual:0.1f} cm", end="")

#         if dist_actual < mejor_dist:
#             mejor_dist = dist_actual
#             pasos_desde_mejor = 0 
#             print(" (Récord actualizado)")
#         else:
#             pasos_desde_mejor += 1
#             print(f" (+{pasos_desde_mejor} pasos desde el mínimo)")

#         if dist_actual > (mejor_dist + ruido_tolerancia):
#             print(f"✅ Mínimo superado. Retrocediendo {pasos_desde_mejor} paso(s) exacto(s).")
            
#             for _ in range(pasos_desde_mejor):
#                 if turningDir == 'r':
#                     hardware_girar_izquierda(spinTime, power)
#                 else:
#                     hardware_girar_derecha(spinTime, power)
#                 sleep_preciso_hardware(timeBetweenSteps)
#             break

#         intentos += 1

#     if intentos == max_intentos:
#         print("⚠️ Orientación terminada por límite de intentos.")
    
#     print(f"🏁 Robot alineado. Distancia final aprox: {mejor_dist:0.1f} cm\n")

def orientate():
    ref = buscar_mejor_pared()

    if not ref:
        return

    print(f"\n🧭 Iniciando alineación inteligente con pared: {ref}")
    power = 0.15
    spinTime = 0.15
    timeBetweenSteps = 0.2

    pasos_totales = 16
    datos_barrido = []

    if(lastTurn == 'l'):
        for _ in range(int(pasos_totales/4)):
            hardware_girar_izquierda(spinTime, power)
            time.sleep(timeBetweenSteps)

        pasos_barrido = int(pasos_totales*(3/4))
        for _ in range(pasos_barrido):
            dist = leer_distancia_robusta(ref)
            datos_barrido.append(dist)
            
            # Giramos un paso a la derecha
            hardware_girar_derecha(spinTime, power)

        time.sleep(timeBetweenSteps)
        datos_suavizados = np.convolve(datos_barrido, np.ones(3)/3, mode='valid')
        idx_min = np.argmin(datos_suavizados)

        pasos_a_volver = pasos_barrido - idx_min + 1

        for _ in range(pasos_a_volver):
            hardware_girar_izquierda(spinTime, power)
            time.sleep(timeBetweenSteps)

    elif(lastTurn == 'r'):
        for _ in range(int(pasos_totales/4)):
            hardware_girar_derecha(spinTime, power)
            time.sleep(timeBetweenSteps)

        pasos_barrido = int(pasos_totales*(3/4))
        for _ in range(pasos_barrido):
            dist = leer_distancia_robusta(ref)
            datos_barrido.append(dist)
            
            # Giramos un paso a la derecha
            hardware_girar_izquierda(spinTime, power)

        time.sleep(timeBetweenSteps)
        datos_suavizados = np.convolve(datos_barrido, np.ones(3)/3, mode='valid')
        idx_min = np.argmin(datos_suavizados)

        pasos_a_volver = pasos_barrido - idx_min + 1

        for _ in range(pasos_a_volver):
            hardware_girar_derecha(spinTime, power)
            time.sleep(timeBetweenSteps)
    
    else:
        for _ in range(int(pasos_totales/2)):
            hardware_girar_izquierda(spinTime, power)
            time.sleep(timeBetweenSteps)

            pasos_barrido = pasos_totales
        for _ in range(pasos_barrido):
            dist = leer_distancia_robusta(ref)
            datos_barrido.append(dist)
            
            # Giramos un paso a la derecha
            hardware_girar_derecha(spinTime, power)

        time.sleep(timeBetweenSteps)
        datos_suavizados = np.convolve(datos_barrido, np.ones(3)/3, mode='valid')
        idx_min = np.argmin(datos_suavizados)

        pasos_a_volver = pasos_barrido - idx_min + 1

        for _ in range(pasos_a_volver):
            hardware_girar_izquierda(spinTime, power)
            time.sleep(timeBetweenSteps)

    np.set_printoptions(precision=4, suppress=True)
    print("Barrido: ")
    print(np.array(datos_barrido))
    print("Suavizados: ")
    print(np.array(datos_suavizados))
    print(f"ArgMin: {idx_min}")

#Camera related functions
# def stream_video_pi():
#     while True:
#         try:
#             inicio_conexion = time.time()
#             ws = websocket.WebSocket()
#             ws.connect(WS_VIDEO_URL, timeout=3) 
#             print("🟢 Conexión de vídeo establecida con FastAPI.")
            
#             while True:
#                 if time.time() - inicio_conexion > 30:
#                     ws.close()
#                     break
                
#                 if MODO_SIMULACION:
#                     frame = np.zeros((616, 820, 3), dtype=np.uint8) # Pantalla negra
#                 else:
#                     frame_yuv = picam2.capture_array("lores")
#                     frame = cv2.cvtColor(frame_yuv, cv2.COLOR_YUV2BGR_I420)
                
#                 if not camara_activa.is_set():
#                     camara_activa.set()
                
#                 success, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 30])
#                 if not success: continue
                
#                 frame_b64 = base64.b64encode(buffer).decode('utf-8')
                
#                 try:
#                     ws.send(frame_b64)
#                 except Exception:
#                     break 
                
#                 time.sleep(0.05)
#         except Exception:
#             time.sleep(0.2)

# def getRotationAngle():
#     frame_yuv = picam2.capture_array("main")
#     frame_bgr = cv2.cvtColor(frame_yuv, cv2.COLOR_YUV2BGR_I420)

#     outputXSize = 800
#     latRate = 1/4 
#     nTilesInVArea = 4.5
#     latMargin = outputXSize * latRate / 2

#     h, w = frame_bgr.shape[:2]
#     scale_x, scale_y = w / 2380, h / 2464

#     pts_src = np.array([[322, 2463], [2956, 2463], [1886, 872], [1394, 872]], dtype=np.float32)
#     pts_src[:, 0] *= scale_x  
#     pts_src[:, 1] *= scale_y  

#     pts_dst = np.array([
#         [latMargin, outputCameraRes[1]], 
#         [outputCameraRes[0] - latMargin, outputCameraRes[1]], 
#         [outputCameraRes[0] - latMargin, 0], 
#         [latMargin, 0]
#     ], dtype=np.float32)
    
#     H = cv2.getPerspectiveTransform(pts_src, pts_dst)

#     img_hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
#     lower_brown = np.array([163, 60, 53])
#     upper_brown = np.array([179, 101, 163])
#     mask_orig = cv2.inRange(img_hsv, lower_brown, upper_brown)

#     # 4. Vista de Pájaro (Solo deformamos la máscara blanca/negra, ¡es mucho más rápido!)
#     mask_bird = cv2.warpPerspective(mask_orig, H, (outputCameraRes[0], outputCameraRes[1]), borderValue=0)

#     # 5. Detección de Bordes (Analizamos solo el 50% inferior, lo que está justo frente al robot)
#     bottom_half = int(outputCameraRes[1] * 0.5)
#     edges = cv2.Canny(mask_bird[bottom_half:, :], 50, 150)
#     lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=40, minLineLength=50, maxLineGap=15)

#     if lines is None:
#         return 0.0

#     angles = []
#     weights = []

#     # 6. Cálculo del Ángulo Ponderado
#     for line in lines:
#         x1, y1, x2, y2 = line[0]
#         # Aseguramos que el vector siempre apunte "hacia arriba" (y negativo en la imagen)
#         if y2 > y1: 
#             x1, y1, x2, y2 = x2, y2, x1, y1
            
#         dx, dy = x2 - x1, y1 - y2
        
#         if dx != 0 or dy != 0:
#             tilt = 90.0 - np.degrees(np.arctan2(dy, dx))
            
#             # Ampliamos la tolerancia: si el robot está torcido hasta 35 grados, lo detectamos
#             if -35 < tilt < 35:
#                 # Teorema de Pitágoras para sacar la longitud de la línea (su peso)
#                 length = np.sqrt(dx**2 + dy**2)
#                 angles.append(tilt)
#                 weights.append(length)

#     if not angles:
#         return 0.0

#     # Matemáticas de campeonato: La pared más larga domina el ángulo final
#     best_tilt = np.average(angles, weights=weights)

#     print(best_tilt)

#     return float(best_tilt)


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

    pts_src = np.array([[322, 2463], [2956, 2463], [1886, 872], [1394, 872]], dtype=np.float32)
    pts_src[:, 0] *= scale_x  
    pts_src[:, 1] *= scale_y  

    pts_dst = np.array([[latMargin, HEIGHT], [WIDTH - latMargin, HEIGHT], [WIDTH - latMargin, 0], [latMargin, 0]], dtype=np.float32)
    H = cv2.getPerspectiveTransform(pts_src, pts_dst)
    
    processed_orig = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower_brown = np.array([0, 35, 0])
    upper_brown = np.array([40, 255, 255])
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
    
    return mask_final

# --- Movimiento Físico y Sincronización Directa ---
def sleep_preciso_hardware(segundos):
    if segundos <= 0: return
    objetivo = time.perf_counter() + segundos
    
    margen = 0.002
    tiempo_restante = objetivo - time.perf_counter()
    
    if tiempo_restante > margen:
        time.sleep(tiempo_restante - margen)
        
    while time.perf_counter() < objetivo:
        pass

def detener_motores():
    if not MODO_SIMULACION:
        mA_pwm.value = 0.0
        mA_in1.off()
        mA_in2.off()
        mB_pwm.value = 0.0
        mB_in1.off()
        mB_in2.off()

def hardware_avanzar():
    if not MODO_SIMULACION:
        mA_in1.on(); mA_in2.off(); mA_pwm.value = POTENCIA_MOTORES_AVANCE
        mB_in1.on(); mB_in2.off(); mB_pwm.value = POTENCIA_MOTORES_AVANCE
        
def hardware_girar_con_impulso(potencia):
    if MODO_SIMULACION: return

    impulso_potencia = 0.35 
    
    mA_pwm.value = impulso_potencia
    mB_pwm.value = impulso_potencia
    sleep_preciso_hardware(0.02)

    mA_pwm.value = potencia
    mB_pwm.value = potencia

def hardware_girar_izquierda(tiempo, potencia = None):
    if not MODO_SIMULACION:
        if potencia == None:
            potencia = POTENCIA_MOTORES_GIRO
            
        mA_in1.off(); mA_in2.on()
        mB_in1.on(); mB_in2.off()
        hardware_girar_con_impulso(potencia)

        sleep_preciso_hardware((tiempo - 0.03)*1.1)
        detener_motores()

def hardware_girar_derecha(tiempo, potencia = None):
    if not MODO_SIMULACION:
        if potencia == None:
            potencia = POTENCIA_MOTORES_GIRO
            
        mA_in1.on(); mA_in2.off()
        mB_in1.off(); mB_in2.on()
        hardware_girar_con_impulso(potencia)
        
        sleep_preciso_hardware(tiempo - 0.03)
        detener_motores()

def moveForward(nTiles):
    global tempPos, lastTurn
    if nTiles == 0: return
    
    additions = {'u': (0, 1), 'r': (1, 0), 'd': (0, -1), 'l': (-1, 0)}
    addition = additions.get(tempDir, (0, 0))
    hardware_avanzar()

    for _ in range(nTiles):
        tempPos = (tempPos[0] + addition[0], tempPos[1] + addition[1])
        sync_position_with_server()
        sleep_preciso_hardware(TIEMPO_AVANCE_CASILLA)
        
    detener_motores()
    lastTurn = 'X'
    time.sleep(0.5)

def turnLeft():
    global tempDir, lastTurn
    trans = {'u': 'l', 'r': 'u', 'd': 'r', 'l': 'd'}
    tempDir = trans.get(tempDir, tempDir)
    sync_position_with_server()
    hardware_girar_izquierda(TIEMPO_GIRO)
    lastTurn = 'l'
    time.sleep(0.5)

def turnRight():
    global tempDir, lastTurn
    trans = {'u': 'r', 'r': 'd', 'd': 'l', 'l': 'u'}
    tempDir = trans.get(tempDir, tempDir)
    sync_position_with_server()
    hardware_girar_derecha(TIEMPO_GIRO)
    lastTurn = 'r'
    time.sleep(0.5)

def turnBack():
    global tempDir
    trans = {'u': 'd', 'r': 'l', 'd': 'u', 'l': 'r'}
    tempDir = trans.get(tempDir, tempDir)
    sync_position_with_server()
    hardware_girar_derecha(TIEMPO_GIRO * 2)
    lastTurn = 'r'
    time.sleep(0.5)

def pickUpKey():
    rele.on()
    time.sleep(10)
    rele.off()

def openDoor():
    print("Puerta")

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
            if MODO_SIMULACION:
                print("📸 Tomando foto simulada de la carpeta...")
                iname = imgNames[image_idx] if image_idx < len(imgNames) else "wall"
                img_path = f"{real}/{iname}.jpg"
                frame_bgr = cv2.imread(img_path)
            else:
                print("📸 Tomando foto simulada de la carpeta...")
                iname = imgNames[image_idx] if image_idx < len(imgNames) else "wall"
                img_path = f"{real}/{iname}_reduced.jpg"
                frame_bgr = cv2.imread(img_path)

                # print("📸 Tomando foto para YOLO y Homografía...")
                # frame_yuv = picam2.capture_array("main")
                # frame_bgr = cv2.cvtColor(frame_yuv, cv2.COLOR_YUV2BGR_I420)
            
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
                try:
                    requests.post(f"{SERVER_URL}/interactuar", json={"tipo": 'D'})
                except requests.exceptions.RequestException: pass
                time.sleep(2)
                estado_actual = "ESCANEO"

            elif dest_type == 'K':
                print(f"Acción en casilla: Interactuando con la llave...")

                if not MODO_SIMULACION:
                    pickUpKey()
                
                try:
                    requests.post(f"{SERVER_URL}/interactuar", json={"tipo": 'K'})
                except requests.exceptions.RequestException: pass
                time.sleep(2)
                estado_actual = "SALTO_ESCANEO"


            elif dest_type == '?':
                print("❓ Inspeccionando interrogante (QR)...")
                if MODO_SIMULACION:
                    img_path = f"{real}/{imgQRs[qr_idx] if qr_idx < len(imgQRs) else imgQRs[0]}.jpg"
                    frame = cv2.imread(img_path)
                else:
                    img_path = f"{real}/{imgQRs[qr_idx] if qr_idx < len(imgQRs) else imgQRs[0]}.jpg"
                    frame = cv2.imread(img_path)
                
                    # (Cuando uses la cámara física más adelante, sustituyes lo de arriba por esto:)
                    # frame_yuv = picam2.capture_array("main")
                    # frame_bgr = cv2.cvtColor(frame_yuv, cv2.COLOR_YUV2BGR_I420)

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
                        # Si no ha terminado, el robot sigue parado sin hacer nada
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

imgNames = ["img_28", "img_3", "wall", "wall", "wall", "wall", "img_23", "img_7", "img_29", "wall", "wall", "img_53", "wall", "img_34"]
imgQRs = ["img_X", "img_Y", "img_Z"]
    
if __name__ == "__main__":
    try:
        # ⚙️ TIEMPOS DE CALIBRACIÓN
        TIEMPO_AVANCE_CASILLA = 1.0 # Segundos que tarda en avanzar 1 casilla entera
        TIEMPO_GIRO = 1.0           # Segundos que tarda en rotar 90 grados
        POTENCIA_MOTORES_AVANCE = 0.3
        POTENCIA_MOTORES_GIRO = 0.3

        if MODO_SIMULACION:
            print("[💻] INICIANDO EN MODO SIMULACIÓN (PC)...")
        else:
            print("[🤖] INICIANDO EN MODO FÍSICO (RASPBERRY PI)...")
            print("[+] Inicializando pines para los Motores A y B...")
            mA_in1 = OutputDevice(20, initial_value=False)
            mA_in2 = OutputDevice(16, initial_value=False)
            mA_pwm = PWMOutputDevice(12, initial_value=0.0)

            mB_in1 = OutputDevice(6, initial_value=False)
            mB_in2 = OutputDevice(19, initial_value=False)
            mB_pwm = PWMOutputDevice(13, initial_value=0.0)

            print("[+] Preparando pines para los Ultrasonidos...")
            SENSORES = {
                "Delantero": DistanceSensor(echo=11, trigger=8, max_distance=3.0, queue_len=1),
                "Izquierda": DistanceSensor(echo=22, trigger=23, max_distance=3.0, queue_len=1),
                "Derecha":   DistanceSensor(echo=18, trigger=17, max_distance=3.0, queue_len=1),
                "Trasero":  DistanceSensor(echo=9,  trigger=25, max_distance=3.0, queue_len=1)
            }

            print("[+] Inicializando pines para el selenoide...")
            rele = OutputDevice(26, active_high=True, initial_value=False)


            print("[+] Configurando flujo único de vídeo optimizado...")
            config = picam2.create_preview_configuration(
                main={"size": (820, 616), "format": "YUV420"}
            )
            
            config["sensor_mode"] = 0
            picam2.configure(config)
            picam2.start()
            
            print("[+] Calibrando sensor...")
            time.sleep(2.0)

            # # ✅ LANZAMOS EL NUEVO HILO DE VÍDEO PI
            # # threading.Thread(target=stream_video_pi, daemon=True).start()
        
            # print("[*] Esperando a que la cámara capture el primer frame...")
            # camara_activa.wait() # Se detiene aquí hasta que el vídeo funcione
            # print("[+] Cámara lista y transmitiendo. Iniciando robot.")

            # print("[+] Inicializando secuencia del robot físico en la Raspberry Pi.")
        
        # send_reset_command()
        # robot_loop()

        moveForward(1)
        turnLeft()
        orientate()
        turnRight()
        orientate()
        turnBack()
        orientate()
        moveForward(1)

    except KeyboardInterrupt:
        print("\n[!] Simulación detenida manualmente.")

    finally:
        print("\n[*] Apagando motores de forma segura y liberando pines...")
        detener_motores()
        if not MODO_SIMULACION:
            mA_in1.close(); mA_in2.close(); mA_pwm.close()
            mB_in1.close(); mB_in2.close(); mB_pwm.close()
            picam2.stop()
            rele.off()
        print("[+] Hardware liberado. Fin del programa.")
        os._exit(0)