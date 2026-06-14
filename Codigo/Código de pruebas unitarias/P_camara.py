from picamera2 import Picamera2
import time

try:
    print("Intentando conectar con la cámara...")
    picam2 = Picamera2()
    
    # 1. Forzamos la configuración nativa de fotografía (aprovecha el máximo FOV del sensor)
    config = picam2.create_still_configuration()
    picam2.configure(config)
    
    # 2. Arrancamos el sensor
    picam2.start()
    print("[+] Cámara iniciada. Regulando luces y enfoque...")
    
    # IMPORTANTE: Dejamos 2 segundos obligatorios. Si la cámara no tiene tiempo
    # de inicializar sus buffers internos, la captura fallará silenciosamente.
    time.sleep(2.0)
    
    print("¡Capturando y guardando foto en el disco...")
    picam2.capture_file("miau.jpg")
    
    picam2.stop()
    print("[+] ¡Proceso completado! Busca el archivo 'miau.jpg'.")   
    
except Exception as e:
    print(f"ERROR: No se ha podido conectar con la cámara.")
    print(f"Detalle del error: {e}")

# streaming

#from flask import Flask, Response
#from picamera2 import Picamera2
#import time
#import io

#app = Flask(__name__)
#picam2 = Picamera2()
#picam2.start()

#def generate_frames():
#    while True:
#        # Creamos un buffer en memoria para la imagen
#        with io.BytesIO() as stream:
#            # Capturamos un frame rápido en formato JPEG
#            picam2.capture_file(stream, format='jpeg')
#            stream.seek(0)
#            frame = stream.read()
#            
        # Formato necesario para que el navegador entienda que es un video
#        yield (b'--frame\r\n'
#               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        
        # Un pequeño descanso para no ahogar la CPU de la Zero W
#        time.sleep(0.1)

#@app.route('/')
#def index():
    # Esta es la ruta principal que envía el stream
#    return Response(generate_frames(), 
#                    mimetype='multipart/x-mixed-replace; boundary=frame')

#if __name__ == '__main__':
#    print("Servidor de streaming iniciado en http://AWSD.local:5000")
    # Escuchamos en todas las IPs de la red (0.0.0.0) en el puerto 5000
#    app.run(host='0.0.0.0', port=5000, threaded=True)