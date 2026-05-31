import requests
from pathlib import Path
import time

# Change this to your VM's public IP when deploying 
SERVER_URL = "http://34.0.201.131:8080/raspberry"

#Path to resources folder
resources = f"{Path(__file__).parent}/testOutput"

# We need a designed folder to store the latest image sent for processing
def send_robot_step(img_base_name, image_folder="."):
    """
    Simulates the Raspberry Pi taking two pictures and sending them to the server,
    requiring only the base name of the images.
    """
    print(f"Enviando datos al servidor para el paso: {img_base_name}...")
    
    # 1. Automatically construct the expected file paths
    path_cenital = f"{resources}/{img_base_name}_cenitalBW.jpg"
    
    path_resized = f"{resources}/{img_base_name}_resized.jpg"
    
    try:
        # 2. Open the image files using the generated paths
        with open(path_cenital, "rb") as f_cenital, open(path_resized, "rb") as f_resized:
            
            files = {
                "cenital_img": (f"{img_base_name}_cenitalBW.jpg", f_cenital, "image/jpeg"),
                "resized_img": (f"{img_base_name}_resized.jpg", f_resized, "image/jpeg")
            }
            
            data = {
                "img_name": img_base_name
            }
            
            # 3. Make the POST request
            response = requests.post(f"{SERVER_URL}/analyze", files=files, data=data)
            
            if response.status_code == 200:
                print("✅ Análisis completado con éxito!")
                resultado = response.json()
                print(f"➡ Tipo de destino: {resultado.get('destination_type')}")
                print(f"➡ Comandos a ejecutar: {resultado.get('commands')}")
            else:
                print(f"❌ Error del servidor ({response.status_code}): {response.text}")
                
    except FileNotFoundError as e:
        print(f"❌ Error: Faltan imágenes. Asegúrate de que {path_cenital} y {path_resized} existan. \nDetalle: {e}")
    except requests.exceptions.ConnectionError:
        print("❌ Error: No se pudo conectar al servidor. ¿Está encendido FastAPI?")

def send_reset_command():
    """
    Sends a POST request to the server to wipe the map memory 
    and return the robot to the starting origin (0,0).
    """
    print("Enviando comando de reinicio al servidor...")
    
    reset_url = f"{SERVER_URL}/reset" 
    
    try:
        # We don't need to send any files or data payload for this one!
        response = requests.post(reset_url)
        
        if response.status_code == 200:
            print("✅ ¡Mapa reseteado con éxito!")
            resultado = response.json()
            print(f"➡ Mensaje del servidor: {resultado.get('message')}")
        else:
            print(f"❌ Error del servidor ({response.status_code}): {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Error: No se pudo conectar al servidor. ¿Está encendido FastAPI?")






#Area for testing:
# if __name__ == "__main__":
#     send_reset_command()
#     time.sleep(1)
#     send_robot_step("img_28")
#     time.sleep(1)
#     send_robot_step("img_3")
#     time.sleep(1)
#     send_robot_step("wall")
#     time.sleep(1)
#     send_robot_step("wall")
#     time.sleep(1)
#     send_robot_step("img_23")
#     time.sleep(1)
#     send_robot_step("img_31")
#     time.sleep(1)
#     send_robot_step("wall")
#     time.sleep(1)
#     send_robot_step("img_53")
#     time.sleep(1)
#     send_robot_step("wall")
#     time.sleep(1)
#     send_robot_step("img_34")


