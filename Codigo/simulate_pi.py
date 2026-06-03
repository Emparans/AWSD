import requests
from pathlib import Path
from picamera2 import Picamera2
from gpiozero import OutputDevice, PWMOutputDevice
import cv2
import numpy as np
import time
import json
import threading
import websocket
import base64

# URL pública de tu FastAPI en la VM
SERVER_URL = "http://34.0.201.131:8080/raspberry"
WS_VIDEO_URL = "ws://34.0.201.131:8080/control/video_stream"

picam2 = Picamera2()

imageForProcessingName = "proc"
outputCameraRes = (820, 616)
real = Path(__file__).parent / "real"

# Estado de telemetría física del Robot
tempDir = 'r'
tempPos = (0, 0)

# CAMBIO NUEVO: Evento de sincronización para esperar a la cámara
camara_activa = threading.Event()

def stream_video_pi():
    while True:
        try:
            inicio_conexion = time.time()
            ws = websocket.WebSocket()
            ws.connect(WS_VIDEO_URL, timeout=3) 
            print("🟢 Conexión de vídeo establecida con FastAPI.")
            
            while True:
                if time.time() - inicio_conexion > 30:
                    ws.close()
                    break
                
                frame_yuv = picam2.capture_array("lores")
                
                frame = cv2.cvtColor(frame_yuv, cv2.COLOR_YUV2BGR_I420)
                
                if not camara_activa.is_set():
                    camara_activa.set()
                
                success, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 30])
                if not success: continue
                
                frame_b64 = base64.b64encode(buffer).decode('utf-8')
                
                try:
                    ws.send(frame_b64)
                except Exception:
                    break 
                
                time.sleep(0.05)
        except Exception:
            time.sleep(0.2)

def resize_frame(frame):
    if frame is None: return None
    return cv2.resize(frame, outputCameraRes)

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
    
    return mask_final, cv2.resize(img, outputCameraRes)

# --- Movimiento Físico y Sincronización Directa ---
def detener_motores():
    mA_pwm.value = 0.0
    mA_in1.off()
    mA_in2.off()
    mB_pwm.value = 0.0
    mB_in1.off()
    mB_in2.off()

def hardware_avanzar(tiempo):
    mA_in1.off(); mA_in2.on(); mA_pwm.value = POTENCIA_MOTORES / 2
    mB_in1.off(); mB_in2.on(); mB_pwm.value = POTENCIA_MOTORES / 2
    time.sleep(tiempo)
    detener_motores()

def hardware_girar_izquierda(tiempo):
    # Motor A va hacia atrás, Motor B hacia adelante (Giro sobre su propio eje)
    mA_in1.off(); mA_in2.on(); mA_pwm.value = POTENCIA_MOTORES
    mB_in1.on(); mB_in2.off(); mB_pwm.value = POTENCIA_MOTORES
    time.sleep(tiempo)
    detener_motores()

def hardware_girar_derecha(tiempo):
    # Motor A va hacia adelante, Motor B hacia atrás
    mA_in1.on(); mA_in2.off(); mA_pwm.value = POTENCIA_MOTORES
    mB_in1.off(); mB_in2.on(); mB_pwm.value = POTENCIA_MOTORES
    time.sleep(tiempo)
    detener_motores()

def moveForward(nTiles):
    global tempPos
    if nTiles == 0: return
    
    additions = {'u': (0, 1), 'r': (1, 0), 'd': (0, -1), 'l': (-1, 0)}
    addition = additions.get(tempDir, (0, 0))

    for _ in range(nTiles):
        tempPos = (tempPos[0] + addition[0], tempPos[1] + addition[1])
        sync_position_with_server()
        hardware_avanzar(TIEMPO_AVANCE_CASILLA)
        time.sleep(0.5)

def turnLeft():
    global tempDir
    trans = {'u': 'l', 'r': 'u', 'd': 'r', 'l': 'd'}
    tempDir = trans.get(tempDir, tempDir)
    sync_position_with_server()
    hardware_girar_izquierda(TIEMPO_GIRO)
    time.sleep(0.5)

def turnRight():
    global tempDir
    trans = {'u': 'r', 'r': 'd', 'd': 'l', 'l': 'u'}
    tempDir = trans.get(tempDir, tempDir)
    sync_position_with_server()
    hardware_girar_derecha(TIEMPO_GIRO)
    time.sleep(0.5)
def sync_position_with_server():
    try:
        requests.post(f"{SERVER_URL}/update_position", json={"pos": list(tempPos), "dir": tempDir}, timeout=2)
    except requests.exceptions.RequestException: pass

# --- Peticiones de Análisis a la VM ---
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
        elif action == 'b': turnRight(); turnRight()
        moveForward(steps)

# --- Bucle de ejecución principal ---
def robot_loop():
    estado_actual = "ESCANEO" 
    dest_type, commands = None, []
    image_idx = 0
    
    while True:
        if estado_actual == "ESCANEO":
            iname = imgNames[image_idx] if image_idx < len(imgNames) else "wall"
            img_path = f"{real}/{iname}.jpg"
            
            homography, resized = generate_mapping_sources(cv2.imread(img_path))
            if homography is None:
                time.sleep(1); continue
                
            dest_type, commands = send_robot_step(homography, resized)
            if dest_type is None:
                time.sleep(2); continue
                
            image_idx += 1
            estado_actual = "MOVIMIENTO"

        elif estado_actual == "SALTO_ESCANEO":
            dest_type, commands = skip_robot_step()
            if dest_type is None: time.sleep(2); continue
            estado_actual = "MOVIMIENTO"

        elif estado_actual == "MOVIMIENTO":
            if commands:
                print(f"Ejecutando ruta hacia '{dest_type}'. Comandos: {commands}")
                executeCommands(commands)
            estado_actual = "INTERACCION"

        elif estado_actual == "INTERACCION":
            if dest_type == 'X' and not commands:
                print("🏁 Laberinto completado o sin salidas."); break
                
            elif dest_type in ['D', 'K', '?']:
                print(f"Acción en casilla: Interactuando con {dest_type}...")
                try:
                    requests.post(f"{SERVER_URL}/interactuar", json={"tipo": dest_type})
                except requests.exceptions.RequestException: pass
                time.sleep(2)
                estado_actual = "SALTO_ESCANEO" if dest_type in ['K', '?'] else "ESCANEO"
                
            elif dest_type == 'X':
                estado_actual = "ESCANEO"
                
        time.sleep(0.1)

imgNames = ["img_28", "img_3", "wall", "wall", "wall", "wall", "img_23", "img_7", "img_29", "wall", "wall", "img_53", "wall", "img_34"]
    
if __name__ == "__main__":
    try:
        print("[+] Inicializando pines para los Motores A y B...")
        mA_in1 = OutputDevice(19, initial_value=False)
        mA_in2 = OutputDevice(6, initial_value=False)
        mA_pwm = PWMOutputDevice(13, initial_value=0.0)

        mB_in1 = OutputDevice(16, initial_value=False)
        mB_in2 = OutputDevice(20, initial_value=False)
        mB_pwm = PWMOutputDevice(12, initial_value=0.0)

        # ⚙️ TIEMPOS DE CALIBRACIÓN (Cámbialos según lo que tarde físicamente tu robot)
        TIEMPO_AVANCE_CASILLA = 0.8 # Segundos que tarda en avanzar 1 casilla entera
        TIEMPO_GIRO = 0.8           # Segundos que tarda en rotar 90 grados
        POTENCIA_MOTORES = 0.5      # 1.0 = 100%, 0.5 = 50%
        
        print("[+] Configurando Doble Flujo de vídeo en hardware...")
        
        config = picam2.create_preview_configuration(
            main={"size": (3280, 2464), "format": "RGB888"},
            lores={"size": (820, 616), "format": "YUV420"}
        )
        config["sensor_mode"] = 0
        picam2.configure(config)
        picam2.start()
        
        print("[+] Calibrando sensor...")
        time.sleep(2.0)

        print("[+] Inicializando secuencia del robot físico en la Raspberry Pi.")
        
        # ✅ LANZAMOS EL NUEVO HILO DE VÍDEO PI
        threading.Thread(target=stream_video_pi, daemon=True).start()
        
        print("[*] Esperando a que la cámara capture el primer frame...")
        camara_activa.wait() # Se detiene aquí hasta que el vídeo funcione
        print("[+] Cámara lista y transmitiendo. Iniciando robot.")
        
        send_reset_command()
        #robot_loop()

        moveForward(1)

    except KeyboardInterrupt:
        print("\n[!] Simulación detenida manualmente.")

    finally:
        print("\n[*] Apagando motores de forma segura y liberando pines...")
        detener_motores()
        mA_in1.close(); mA_in2.close(); mA_pwm.close()
        mB_in1.close(); mB_in2.close(); mB_pwm.close()
        print("[+] Hardware liberado. Fin del programa.")