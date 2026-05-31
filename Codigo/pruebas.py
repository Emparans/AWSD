from gpiozero import DistanceSensor, OutputDevice
import time

# 1. Inicializar el Relé
rele = OutputDevice(26, active_high=True, initial_value=False)

# 2. Inicializar los 4 sensores de ultrasonidos
sensor_inferior  = DistanceSensor(echo=18, trigger=17)   #-------------------
sensor_delantero = DistanceSensor(echo=19, trigger=16)   #-------------------
sensor_izquierdo = DistanceSensor(echo=22, trigger=23)   
sensor_derecho   = DistanceSensor(echo=6, trigger=12)

try:
    print("Iniciando lecturas... Presiona Ctrl+C para salir.")
    while True:
        # Multiplicamos por 100 para obtener la distancia en centímetros
        dist_detras = sensor_inferior.distance * 100
        dist_delant = sensor_delantero.distance * 100
        dist_izq = sensor_izquierdo.distance * 100
        dist_der = sensor_derecho.distance * 100
        
        print(f"INF: {dist_detras:.1f}cm | DEL: {dist_delant:.1f}cm | IZQ: {dist_izq:.1f}cm | DER: {dist_der:.1f}cm")
        
        # Aquí puedes meter tu lógica, por ejemplo:
        if dist_delant < 10:
             rele.on()
        else:            
            rele.off()
            
        time.sleep(2) # Un pequeño respiro entre lecturas

except KeyboardInterrupt:
    print("\nApagando sistema de forma segura...")
finally:
    # Cerramos todo para asegurarnos de que NINGÚN pin se quede "busy" para la próxima vez

    time.sleep(2)
    sensor_inferior.close()
    sensor_delantero.close()
    sensor_izquierdo.close()
    sensor_derecho.close()
    rele.close()