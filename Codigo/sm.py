import asyncio
import io
import websockets
from picamera2 import Picamera2

# Configuración de tu VM en Google Cloud
SERVER_URL = "ws://34.175.45.244:8080/control/stream"

async def stream_video():
    print("Intentando conectar con la cámara...")
    picam2 = Picamera2()
    
    # 1. Configuramos vídeo pero FORZANDO el FOV completo (Full Sensor)
    # Usamos una resolución baja (640x480) para que la Pi Zero no sufra
    config = picam2.create_video_configuration(
    main={
        "size": (1640, 1232),  # sin zoom raro + ligero
        "format": "RGB888"
    }
)
    
    # Este paso es el secreto: le dice al driver que use todo el ancho del sensor
    # evitando el recorte automático (zoom) que hace el modo vídeo por defecto.
    config["sensor_mode"] = 0  # Modo 0 suele ser la resolución completa del sensor
    
    picam2.configure(config)
    
    # 2. Arrancamos el sensor
    picam2.start()
    print("[+] Cámara iniciada con FOV completo y optimizada para vídeo...")
    
    # Tiempo para regular el brillo
    await asyncio.sleep(2.0)
    
    print("Conectando al servidor de Google Cloud...")
    try:
        async with websockets.connect(SERVER_URL) as ws:
            print("[🟢 OK] Conectado. Transmitiendo en tiempo real...")
            
            while True:
                with io.BytesIO() as stream:
                    # Usamos capture_file pero al estar en modo vídeo es inmediato
                    picam2.capture_file(stream, format='jpeg')
                    stream.seek(0)
                    frame_bytes = stream.read()
                
                try:
                    await ws.send(frame_bytes)
                    # Bajamos un pelín el delay para ganar más FPS en la Pi Zero W
                    await asyncio.sleep(0.02) 
                    
                except Exception as e:
                    print(f"Error al enviar datos: {e}")
                    break

    except Exception as e:
        print(f"No se pudo conectar al servidor: {e}")
        
    finally:
        print("Cerrando cámara...")
        picam2.stop()

# Arrancamos el bucle asíncrono
asyncio.run(stream_video())