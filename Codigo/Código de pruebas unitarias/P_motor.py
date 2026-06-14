from gpiozero import OutputDevice, PWMOutputDevice
import time

print("[+] Inicializando pines para los Motores A y B...")

# --- MOTOR A (IZQUIERDO) ---
mA_in1 = OutputDevice(20, initial_value=False)
mA_in2 = OutputDevice(16, initial_value=False)
mA_pwm = PWMOutputDevice(12, initial_value=0.0)

# --- MOTOR B (DERECHO) ---
mB_in1 = OutputDevice(6, initial_value=False)
mB_in2 = OutputDevice(19, initial_value=False)
mB_pwm = PWMOutputDevice(13, initial_value=0.0)


# ---------------- FUNCIONES ----------------

def detener_motores():
    """Detiene ambos motores simultáneamente."""
    mA_pwm.value = 0.0
    mB_pwm.value = 0.0

    mA_in1.off()
    mA_in2.off()
    mB_in1.off()
    mB_in2.off()


def adelante(potencia=0.5):
    print("[->] Adelante")
    mA_in1.on(); mA_in2.off()
    mB_in1.on(); mB_in2.off()
    mA_pwm.value = potencia
    mB_pwm.value = potencia


def atras(potencia=0.5):
    print("[<-] Atrás")
    mA_in1.off(); mA_in2.on()
    mB_in1.off(); mB_in2.on()
    mA_pwm.value = potencia
    mB_pwm.value = potencia


def izquierda(potencia=0.5):
    print("[↺] Izquierda")
    # Motor A atrás, Motor B adelante
    mA_in1.off(); mA_in2.on()
    mB_in1.on(); mB_in2.off()
    mA_pwm.value = potencia
    mB_pwm.value = potencia


def derecha(potencia=0.5):
    print("[↻] Derecha")
    # Motor A adelante, Motor B atrás
    mA_in1.on(); mA_in2.off()
    mB_in1.off(); mB_in2.on()
    mA_pwm.value = potencia
    mB_pwm.value = potencia


# ---------------- PRUEBA ----------------

try:
    print("\n=== PRUEBA UNITARIA: MOTORES A y B ===")
    print("[!] Levanta las ruedas de la mesa para la prueba.")
    time.sleep(1.5)

    adelante(0.5)
    time.sleep(1)

    detener_motores()
    time.sleep(3)

    atras(0.5)
    time.sleep(1)

    detener_motores()
    time.sleep(3)

    izquierda(0.3)
    time.sleep(1)

    detener_motores()
    time.sleep(3)

    derecha(0.3)
    time.sleep(1)

    detener_motores()

    print("\n[+] Prueba finalizada.")

except KeyboardInterrupt:
    print("\n[!] Prueba cancelada por el usuario.")

finally:
    print("\n[*] Apagando motores de forma segura y liberando pines...")
    detener_motores()

    mA_in1.close()
    mA_in2.close()
    mA_pwm.close()

    mB_in1.close()
    mB_in2.close()
    mB_pwm.close()

    print("[+] Pines liberados correctamente.")