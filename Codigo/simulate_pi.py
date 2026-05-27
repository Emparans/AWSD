import requests
from pathlib import Path

# Change this to your VM's public IP when deploying 
SERVER_URL = "http://34.175.45.244:8080/raspberry/analyze"

def send_robot_step(img_base_name, image_folder="."):
    """
    Simulates the Raspberry Pi taking two pictures and sending them to the server,
    requiring only the base name of the images.
    """
    print(f"Enviando datos al servidor para el paso: {img_base_name}...")
    
    # 1. Automatically construct the expected file paths
    path_cenital = f"{Path(__file__).parent}/{img_base_name}_cenitalBW.jpg"
    
    path_resized = f"{Path(__file__).parent}/{img_base_name}_resized.jpg"
    
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
            response = requests.post(SERVER_URL, files=files, data=data)
            
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

if __name__ == "__main__":
    send_robot_step(img_base_name="img_5")