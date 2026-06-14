from gpiozero import OutputDevice
from time import sleep

# Configuramos el pin GPIO 4 como salida para el relé
# Active_high=True suele ser lo normal, pero si tu relé funciona 
# al revés (se activa cuando el pin está bajo), cámbialo a False.
rele = OutputDevice(26, active_high=True, initial_value=False)

print("Iniciando prueba del electroimán en GPIO 4...")
print("Presiona Ctrl+C para detener la prueba.")

try:
    while True:
        print("Electroimán ACTIVADO")
        rele.on()  # Cierra el relé
        sleep(6)   # Mantiene activado 2 segundos

        print("Electroimán DESACTIVADO")
        rele.off() # Abre el relé
        sleep(3)   # Mantiene desactivado 2 segundos

except KeyboardInterrupt:
    print("\nPrueba detenida por el usuario.")
    rele.off() # Aseguramos que el imán se apague al salir
    print("Relé desactivado por seguridad.")