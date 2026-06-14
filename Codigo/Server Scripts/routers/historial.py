from fastapi import APIRouter, HTTPException, Body
from google.cloud import storage
import json
import state
from datetime import datetime
from zoneinfo import ZoneInfo
import state

# Creació d'un router per agrupar tots els endpoints sota el prefix "/historial"
router = APIRouter()

# Nom del bucket (contenidor) a Google Cloud Storage on es guarden els mapes
NOMBRE_BUCKET = "awsd-mapas"

# Inicialització del client de Cloud Storage (utilitza les credencials per defecte del projecte GCP)
storage_client = storage.Client()

# ------------------- LLISTAT DE MAPES -------------------

@router.get("/historial/obtenerMapas")
async def listarMapas():
    try:
        # Obté una llista de tots els blobs (fitxers) dins del bucket
        blobs = storage_client.bucket(NOMBRE_BUCKET).list_blobs()
        # Filtra perquè només es mostrin els fitxers amb extensió .json
        return {"mapas": [b.name for b in blobs if b.name.endswith('.json')]}
    except Exception as e:
        print(f"Error listar mapas: {e}")
        return {"mapas": []} 

# ------------------- OBTENIR UN MAPA CONCRET -------------------

@router.get("/historial/obtenerMapa/{nombre_archivo}")
async def obtener_contenido_json(nombre_archivo: str):
    try:
        # Accedeix al blob (fitxer) dins del bucket
        blob = storage_client.bucket(NOMBRE_BUCKET).blob(nombre_archivo)
        # Descarrega el contingut com a text
        contenido = blob.download_as_text()
        # Converteix el text JSON a un diccionari Python i el retorna
        return json.loads(contenido)
    except Exception as e:
        print(f"Error al descargar {nombre_archivo}: {e}")
        return {"error": str(e)}

# ------------------- GUARDAR UN NOU MAPA (HISTORIAL) -------------------

@router.post("/historial/guardar")
async def guardar_historial(nombre: str = Body(..., embed=True),
                            creador: str = Body(..., embed=True)):
    """
    Guarda l'estat actual del robot (mapa, puntuació, etc.) a Cloud Storage.
    Rep dos paràmetres per body (en format JSON):
        - nombre: nom que l'usuari vol donar al mapa.
        - creador: nom de la persona/equip que realitza el recorregut.
    Afegeix data, hora, puntuació i temps (placeholder) al JSON abans de pujar-lo.
    """
    try:
        # Neteja espais en blanc i prepara els noms
        nombre_mapa = nombre.strip()
        creador_mapa = creador.strip()

        # Obté la data i hora actual a la zona horària d'Espanya (Europe/Madrid)
        zona_local = ZoneInfo("Europe/Madrid") 
        fecha_actual = datetime.now(zona_local).strftime("%d/%m/%Y a las %H:%M:%S")
        
        # Obté l'estat actual del robot (mapa + telemetria) en format JSON
        mapa_json_str = state.robot_lab.toJSON()
        contenido_json = json.loads(mapa_json_str)

        # Assegura que existeix la clau "state" dins del JSON
        if "state" not in contenido_json:
            contenido_json["state"] = {}
            
        # Afegeix informació addicional a l'apartat "state"
        contenido_json["state"]["score"] = state.robot_lab.score # Puntuació final
        contenido_json["state"]["tiempo"] = state.robot_lab.time # Temps final
        contenido_json["state"]["fecha"] = fecha_actual          # Data i hora actual
        contenido_json["state"]["creador"] = creador_mapa        # Nom del creador

        # Accedeix al bucket (el crea si no existeix, però normalment ja està creat)
        bucket = storage_client.get_bucket(NOMBRE_BUCKET) 
        
        # Construeix el nom de l'arxiu: nom_mapa.json
        nombre_archivo_gcs = f"{nombre_mapa}.json"
        blob = bucket.blob(nombre_archivo_gcs)
        
        # Puja el contingut JSON al bucket (convertint-lo a string amb indentació i suport UTF-8)
        blob.upload_from_string(
            data=json.dumps(contenido_json, indent=4, ensure_ascii=False),
            content_type="application/json"
        )
        
        print(f"¡Éxito! Archivo guardado en Cloud Storage como: {nombre_archivo_gcs}")
        
        return {
            "status": "ok", 
            "mensaje": f"Partida guardada en Cloud Storage como {nombre_archivo_gcs}"
        }
        
    # Tractament d'excepcions
    except HTTPException as he:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar en Storage: {str(e)}")


@router.delete("/historial/eliminar/{nombre_archivo}")
async def eliminar_mapa(nombre_archivo: str):
    """
    Elimina un fitxer de mapa del bucket.
    El paràmetre 'nombre_archivo' pot arribar amb o sense extensió .json.
    Es neteja i s'assegura que el nom tingui l'extensió .json abans d'eliminar.
    """
    try:
        bucket = storage_client.get_bucket(NOMBRE_BUCKET)
        
        # Neteja el nom: treu extensió si en té, elimina espais, i després afegeix .json
        nombre_limpio = nombre_archivo.replace('.json', '').strip()
        nombre_real_gcs = f"{nombre_limpio}.json"
        
        blob = bucket.blob(nombre_real_gcs)
        
        # Comprova si l'arxiu existeix abans d'intentar eliminar
        if not blob.exists():
            print(f"Archivo {nombre_real_gcs} no existe")
            raise HTTPException(status_code=404, detail=f"El archivo {nombre_real_gcs} no existe en Cloud Storage")
            
        blob.delete() # Elimina el blob
        
        return {
            "status": "ok",
            "mensaje": f"El mapa {nombre_real_gcs} ha sido eliminado correctamente."
        }
        
    # Tractament d'excepcions
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error interno: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al eliminar en Storage: {str(e)}")