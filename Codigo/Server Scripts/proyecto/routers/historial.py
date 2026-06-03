from fastapi import APIRouter, HTTPException, Body  # <- AÑADIDO: Body
from google.cloud import storage
import json

router = APIRouter()

NOMBRE_BUCKET = "awsd-mapas"
storage_client = storage.Client()


@router.get("/historial/obtenerMapas")
async def listarMapas():
    try:
        blobs = storage_client.bucket(NOMBRE_BUCKET).list_blobs()
        return {"mapas": [b.name for b in blobs if b.name.endswith('.json')]}
    except Exception as e:
        print(f"❌ ERROR al listar mapas: {e}")
        return {"mapas": []} 


@router.get("/historial/obtenerMapa/{nombre_archivo}")
async def obtener_contenido_json(nombre_archivo: str):
    try:
        blob = storage_client.bucket(NOMBRE_BUCKET).blob(nombre_archivo)
        contenido = blob.download_as_text()
        return json.loads(contenido)
    except Exception as e:
        print(f"❌ ERROR al descargar {nombre_archivo}: {e}")
        return {"error": str(e)}


@router.post("/historial/guardar")
# MODIFICADO: Recibe el string directamente del JSON sin clases intermedias
async def guardar_historial(nombre: str = Body(..., embed=True),  
                            creador: str = Body(..., embed=True)):
    try:
        nombre_mapa = nombre.strip()
        nombre_creador = creador.strip()
        
        # 1. Leer el archivo map.json que ya está en tu VM
        try:
            with open("map.json", "r", encoding="utf-8") as f:
                contenido_json = json.load(f)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="El archivo map.json no existe en la VM")

        # 2. Conectar con el bucket
        bucket = storage_client.get_bucket(NOMBRE_BUCKET) 
        
        # Definimos el nombre del nuevo archivo en Cloud Storage
        nombre_archivo_gcs = f"{nombre_mapa}.json"
        blob = bucket.blob(nombre_archivo_gcs)
        
        # 3. Subir el contenido directamente como JSON string
        blob.upload_from_string(
            data=json.dumps(contenido_json, indent=4),
            content_type="application/json"
        )
        
        print(f"¡Éxito! Archivo guardado en Cloud Storage como: {nombre_archivo_gcs}")
        
        return {
            "status": "ok", 
            "mensaje": f"Partida guardada en Cloud Storage como {nombre_archivo_gcs}"
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar en Storage: {str(e)}")


@router.delete("/historial/eliminar/{nombre_archivo}")
async def eliminar_mapa(nombre_archivo: str):
    try:
        bucket = storage_client.get_bucket(NOMBRE_BUCKET)
        
        # CORRECCIÓN: Nos aseguramos de limpiar cualquier .json repetido y añadirlo de forma controlada
        nombre_limpio = nombre_archivo.replace('.json', '').strip()
        nombre_real_gcs = f"{nombre_limpio}.json"
        
        blob = bucket.blob(nombre_real_gcs)
        
        # Comprobamos si el mapa existe antes de intentar borrarlo
        if not blob.exists():
            print(f"❌ El archivo {nombre_real_gcs} no existe en el bucket.")
            raise HTTPException(status_code=404, detail=f"El archivo {nombre_real_gcs} no existe en Cloud Storage")
            
        # Eliminamos el archivo del bucket
        blob.delete()
        print(f"🗑️ Archivo eliminado con éxito de Cloud Storage: {nombre_real_gcs}")
        
        return {
            "status": "ok",
            "mensaje": f"El mapa {nombre_real_gcs} ha sido eliminado correctamente."
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"❌ Error interno en el servidor: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al eliminar en Storage: {str(e)}")