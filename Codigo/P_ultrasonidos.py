from gpiozero import DistanceSensor
from time import sleep

# Definimos los pines: trigger en el 23 y echo en el 24
sensor = DistanceSensor(echo=11, trigger=8)   

print("Probando sensor de ultrasonidos...")
print("Presiona Ctrl+C para salir")

try:
    while True:
        # La distancia viene en metros, la pasamos a cm multiplicando por 100
        distancia_cm = sensor.distance * 100
        print(f"Distancia: {distancia_cm:.2f} cm")
        sleep(0.5)

except KeyboardInterrupt:
    print("\nPrueba terminada.")