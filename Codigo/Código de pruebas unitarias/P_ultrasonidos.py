from gpiozero import DistanceSensor
from time import sleep

# Configuración de los sensores (Ajusta los pines GPIO según tus conexiones)
# Estructura: 'Nombre': DistanceSensor(echo=PIN_ECHO, trigger=PIN_TRIGGER)
sensores = {
    "Delantero": DistanceSensor(echo=11, trigger=8),
    "Izquierda":  DistanceSensor(echo=22, trigger=23),   # <--- Cambia estos pines
    "Derecha":    DistanceSensor(echo=18, trigger=17),    # <--- Cambia estos pines
    "Inferior":   DistanceSensor(echo=9, trigger=25)   # <--- Cambia estos pines
}

print("Probando los 4 sensores de ultrasonidos (AWSD)...")
print("Presiona Ctrl+C para salir\n")

try:
    while True:
        lecturas = []
        
        # Iteramos de forma limpia por cada sensor
        for nombre, sensor in sensores.items():
            # Convertimos de metros a centímetros
            distancia_cm = sensor.distance * 100
            lecturas.append(f"{nombre}: {distancia_cm:.1f} cm")
        
        # Imprime las 4 lecturas en una sola línea para que no sature la terminal
        print(" | ".join(lecturas))
        
        # Un pequeño delay para no saturar el procesador y evitar interferencias
        sleep(0.4)

except KeyboardInterrupt:
    print("\nPrueba de sensores terminada.")