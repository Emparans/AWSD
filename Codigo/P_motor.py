from gpiozero import OutputDevice, PWMOutputDevice
import time

print("[+] Inicializando pines para los Motores A y B...")

# --- CONFIGURACIÓN MOTOR A ---
# Dirección: Pines digitales normales
mA_in1 = OutputDevice(19, initial_value=False)
mA_in2 = OutputDevice(6, initial_value=False)
# Velocidad: Pin con capacidad PWM
mA_pwm = PWMOutputDevice(13, initial_value=0.0)

# --- CONFIGURACIÓN MOTOR B ---
# Dirección: Cambia estos números por los pines GPIO que uses para el Motor B
mB_in1 = OutputDevice(16, initial_value=False)
mB_in2 = OutputDevice(20, initial_value=False)
# Velocidad: Pin con capacidad PWM para el Motor B
mB_pwm = PWMOutputDevice(12, initial_value=0.0)

def detener_motores():
    """Detiene ambos motores simultáneamente."""
    # Detener Motor A
    mA_pwm.value = 0.0
    mA_in1.off()
    mA_in2.off()
    
    # Detener Motor B
    mB_pwm.value = 0.0
    mB_in1.off()
    mB_in2.off()

try:
    print("\n=== PRUEBA UNITARIA: MOTORES A y B ===")
    print("[!] Levanta las ruedas de la mesa para la prueba.")
    time.sleep(1.5)

    # 1. Ambos hacia adelante con distintas potencias
    print("\n[->] Ambos hacia ADELANTE")
    print("     Motor A: 100% | Motor B: 50%")
    
    # Configurar Motor A
    mA_in1.on()
    mA_in2.off()
    mA_pwm.value = 1.0  # 100% potencia
    
    # Configurar Motor B
    mB_in1.on()
    mB_in2.off()
    mB_pwm.value = 1.0  # 50% potencia
    
    time.sleep(5)

    # 2. Parada corta
    print("\n[---] Pausa de 1 segundo...")
    detener_motores()
    time.sleep(1)

    # 3. Direcciones opuestas y distintas potencias
    print("\n[<->] Direcciones independientes")
    print("      Motor A: ATRÁS (30%) | Motor B: ADELANTE (80%)")
    
    # Configurar Motor A
    mA_in1.on()
    mA_in2.off()
    mA_pwm.value = 1.0  # 30% potencia
    
    # Configurar Motor B
    mB_in1.on()
    mB_in2.off()
    mB_pwm.value = 1.0  # 80% potencia
    
    time.sleep(5)

    print("\n[+] Prueba de los Motores finalizada.")

except KeyboardInterrupt:
    print("\n[!] Prueba cancelada por el usuario.")

finally:
    print("\n[*] Apagando motores de forma segura y liberando pines...")
    detener_motores()
    
    # Liberamos los pines GPIO para que no se queden bloqueados
    mA_in1.close()
    mA_in2.close()
    mA_pwm.close()
    
    mB_in1.close()
    mB_in2.close()
    mB_pwm.close()
    
    print("[+] Pines liberados correctamente.")