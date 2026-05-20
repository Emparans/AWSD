import bpy
import os
import random
import math

from bpy_extras.object_utils import world_to_camera_view

#variables
scene = bpy.context.scene
rutaTexturas = "C:/Users/jempa/Desktop/h/Texturas/"

ruta = "C:/Users/jempa/Desktop/h"
seed = 0
#48712


carpeta_fondos = os.path.join(ruta, "random_background")
paredes = bpy.data.collections.get("ParedesClave").objects
puerta = bpy.data.objects["Puerta"]
centroLlave = bpy.data.objects["Centro"]
llave = bpy.data.objects["Llave"]
soporte = bpy.data.objects["Soporte"]

interrogantes = bpy.data.objects["interrogante"]
qr = bpy.data.objects["qr"]
llaveSuelo = bpy.data.objects["LlaveSuelo"]

camara = bpy.data.objects["def"]
luz = bpy.data.objects["Luz"]
imprimirPuerta = False
imprimirLlave = False
clasePuerta = -1
claseLlave = -1

registro_distancias = []

lista_fondos = [f for f in os.listdir(carpeta_fondos) if f.lower().endswith('.jpg')]

textura = ["estrella","luna","nube","sol"]
clases = ["puerta_estrella","puerta_luna","puerta_nube","puerta_sol",
        "llave_estrella","llave_luna","llave_nube","llave_sol", 
        "interrogacion"]


def clamp(value, minV, maxV):
    return max(minV, min(value, maxV))
    


def get_bbox(obj, scene, cam):
    mat = obj.matrix_world
    nodes = [world_to_camera_view(scene, cam, mat @ v.co) for v in obj.data.vertices]
    
    x_coords = [clamp(n.x, 0.0, 1.0) for n in nodes]
    y_coords = [clamp(n.y, 0.0, 1.0) for n in nodes]
    
    # Calcular centro, ancho y alto normalizados
    x_min, x_max = min(x_coords), max(x_coords)
    y_min, y_max = min(y_coords), max(y_coords)
    
    width = x_max - x_min
    height = y_max - y_min
    x_center = x_min + (width / 2)
    y_center = 1 - (y_min + (height / 2))
    
    return x_center, y_center, width, height


def setupCarpetas():
    #carpetas
    rutaYOLO = ruta + "/dataset"
    carpetas_yolo = [
        os.path.join(rutaYOLO, "test", "images"),
        os.path.join(rutaYOLO, "test", "labels"),
        os.path.join(rutaYOLO, "train", "images"),
        os.path.join(rutaYOLO, "train", "labels"),
        os.path.join(rutaYOLO, "val", "images"),
        os.path.join(rutaYOLO, "val", "labels")
    ]

    for carpeta in carpetas_yolo:
            if not os.path.exists(carpeta):
                # os.makedirs crea toda la ruta (incluyendo carpetas intermedias)
                os.makedirs(carpeta, exist_ok=True)
                print(f"Carpeta creada: {carpeta}")
            else:
                print(f"La carpeta ya existía: {carpeta}")

def cambiarParedes(paredes):
    for p in paredes:
        if(random.randint(0,1) == 0):
            p.hide_viewport = True
            p.hide_render = True
        else:
            p.hide_viewport = False
            p.hide_render = False

def moverLlave(centro):
    offset = random.randint(0,4)
    posicionX = 12.8 - (offset*2.6)
    centro.location = (posicionX,0,0)
    return offset
        
def moverPuerta(puerta, offsetLlave):
    offset = random.randint(0,4)
    
    fixedOffset = clamp(offset + offsetLlave, 0, 4)
    posicionX = 11.5 - (fixedOffset*2.6)
    puerta.location = (posicionX,0,0.01)
    return offset

def moverLlaveSuelo(llavesuelo, offsetLlave):
    offset = random.uniform(0,4)
    offsetY = random.uniform(-1,1)
    fixedOffset = clamp(offset + offsetLlave, 0, 4)
    posicionX = 12.0 - (fixedOffset*2.6)
    
    llaveSuelo.rotation_euler = (0,math.radians(90),math.radians(random.uniform(0,360)))
    llavesuelo.location = (posicionX,offsetY,0.07)

def moverCamara(cam):
    cam.location = (-0.5,random.uniform(-1,1) / 10, 1.8 + (random.uniform(-1,1) / 10))
    
    x = math.radians(75 + random.uniform(-1,1))
    y = math.radians(random.uniform(-1,1))
    z = math.radians(-90 + random.uniform(-2,2))
    cam.rotation_euler = (math.radians(75),0,math.radians(-90))
    cam.rotation_euler = (x, y, z)

def cambiarLuz(luz):
    luz.data.energy = random.uniform(0,50)
    luz.rotation_euler[2] = random.uniform(0, 2 * math.pi)
    luz.rotation_euler[0] = math.radians(random.uniform(-70, 70))


def fondoAleatorio():
    compositor_tree = bpy.data.node_groups.get("Compositor Nodes")
    
   
    nodes = compositor_tree.nodes
    nodo_fondo = None
    for nodo in nodes:
        if nodo.type == 'IMAGE' and nodo.label == "NodoFondo":
            nodo_fondo = nodo
            break
    imagen_elegida = random.choice(lista_fondos)
    ruta_completa = os.path.join(carpeta_fondos, imagen_elegida)
    

    nueva_imagen = bpy.data.images.load(ruta_completa)
    nodo_fondo.image = nueva_imagen
   



def cambiarTextura(objeto):
    mat = objeto.active_material
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    
    #cambiar textura
    tex_node = next((n for n in nodes if n.type == 'TEX_IMAGE'), None)
    if tex_node:
        id = random.randint(0,3)
        img = textura[id]
        nuevaTextura = bpy.data.images.load(f"{rutaTexturas}/{img}.jpg")
        tex_node.image = nuevaTextura
    
    #rotar textura
    mapping_node = next((n for n in nodes if n.type == 'MAPPING'), None)
    if mapping_node:
        rot = random.uniform(0,2*math.pi)
        mapping_node.inputs['Rotation'].default_value[2] = rot
    
    return id

def esconder(o):
    o.hide_viewport = True
    o.hide_render = True
    
def mostrar(o):
    o.hide_viewport = False
    o.hide_render = False


def setupYOLO():
    bpy.context.scene.render.engine = 'BLENDER_EEVEE'
    bpy.context.scene.display.shading.light = 'STUDIO'
    bpy.context.scene.display.shading.color_type = 'MATERIAL'
    bpy.context.scene.render.resolution_x = (3280 // 4)
    bpy.context.scene.render.resolution_y = (2464 // 4)


def guardarFrameYOLO(path):
    cam_obj = bpy.data.objects["def"]
    scene.camera = cam_obj
    scene.render.filepath = os.path.join(path, f"img_{i}.png")
    bpy.ops.render.render(write_still=True)



def guardarLabelYOLO(path):
    targets = ""
    if imprimirPuerta:
        bbox = get_bbox(puerta, scene, scene.camera)
        targets += f"{clasePuerta} {bbox[0]} {bbox[1]} {bbox[2]} {bbox[3]}\n"
          
    if imprimirLlave:
        bbox = get_bbox(llave, scene, scene.camera)
        targets += f"{claseLlave} {bbox[0]} {bbox[1]} {bbox[2]} {bbox[3]}\n"   
    
    if imprimirQR:
        bbox = get_bbox(interrogantes, scene, scene.camera)
        targets += f"8 {bbox[0]} {bbox[1]} {bbox[2]} {bbox[3]}\n" 


    if imprimirObjSuelo:
        bbox = get_bbox(llaveSuelo, scene, scene.camera)
        targets += f"{claseLlaveSuelo} {bbox[0]} {bbox[1]} {bbox[2]} {bbox[3]}\n" 

    with open(os.path.join(path, f"img_{i}.txt"), 'w') as f:
        f.write(targets)


def moverQR(interroganteObj, qrObj):
    interroganteObj.location = ((-0.7416) / 10 ,random.uniform(-1,1) / 10,(8.924+ random.uniform(-1,1)) / 10)
    interroganteObj.rotation_euler = (math.radians(90), math.radians(random.uniform(-10, 10)), math.radians(90))
    scale = random.uniform(1,0.7)
    interroganteObj.scale = (scale, scale*0.5, scale)
    
    qrObj.location = (-0.8416 / 10,0,8.924 / 10)
    qrObj.rotation_euler = (math.radians(90), math.radians(random.uniform(-40, 40)), math.radians(90))
    
    
    mat = qrObj.active_material
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    
    
    #cambiar textura
    tex_node = next((n for n in nodes if n.type == 'TEX_IMAGE'), None)
    if tex_node:
        qrRandom = random.randint(0,8)
        nuevaTextura = bpy.data.images.load(f"{rutaTexturas}/qr{qrRandom}.png")
        tex_node.image = nuevaTextura
    
    

def generarMapa():
    global imprimirPuerta, imprimirLlave, clasePuerta, claseLlave, imprimirQR, imprimirObjSuelo, claseLlaveSuelo
    
    llaveX = moverLlave(centroLlave)
    puertaX = moverPuerta(puerta, llaveX)
    moverLlaveSuelo(llaveSuelo, llaveX)
    cambiarParedes(paredes)
    
    clasePuerta = cambiarTextura(puerta)
    claseLlave = cambiarTextura(llave) + 4
    
    claseLlaveSuelo = cambiarTextura(llaveSuelo) + 4
    #print(claseLlaveSuelo)
    moverQR(interrogantes, qr)
    cambiarLuz(luz)
    
    moverCamara(camara)
    
    if (random.randint(0,1)==0):
        if (random.randint(0,1)==0):
            #mostrar llave
            imprimirLlave = True
            imprimirQR = False
            mostrar(llave)
            mostrar(soporte)
            esconder(qr)
            esconder(interrogantes)
            
        else:
            #mostrar qr
            imprimirLlave = False
            imprimirQR = True
            esconder(llave)
            esconder(soporte)
            mostrar(qr)
            mostrar(interrogantes)
    else:
        imprimirLlave = False
        imprimirQR = False
        esconder(qr)
        esconder(interrogantes)
        esconder(llave)
        esconder(soporte)
        
    if (random.randint(0,1)==0):
        #mostrar puerta
        imprimirPuerta = True
        mostrar(puerta)
    else:
        imprimirPuerta = False
        esconder(puerta)
        
        
        
    if (random.randint(0,0)==1):
        imprimirObjSuelo = True
        mostrar(llaveSuelo)
    else:
        imprimirObjSuelo = False
        esconder(llaveSuelo)
    
    fondoAleatorio()
            
    
    
def setupTopdown():
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'FLAT' 
    scene.display.shading.color_type = 'OBJECT' 
    bpy.context.scene.render.resolution_x = 600
    bpy.context.scene.render.resolution_y = 367    

def guardarTopdown(path):
    x_limite = centroLlave.location.x + 1
    print(f"limite {x_limite}")
    
    # 2. Asignar colores a los objetos
    for obj in bpy.data.objects:
        if obj.type == 'MESH':

            if obj.name == 'ParedLlave':
                obj.color = (1, 1, 1, 1)
                continue
            
            if obj.name in nombres_paredesH:
                if obj.location.x <= x_limite:
                    obj.color = (1, 1, 1, 1) 
                else:
                    
                    obj.color = (0, 0, 0, 1) 
            else:
                obj.color = (0, 0, 0, 1)

    cam_obj = bpy.data.objects["TopCam"]
    scene.camera = cam_obj
    
    scene.render.filepath = os.path.join(path, f"img_{i}.png")
    bpy.ops.render.render(write_still=True)

def calcular_distancia(obj, camara): 
    if obj is None or camara is None:
        return 0.0

    pos_obj = obj.matrix_world.to_translation()
    pos_cam = camara.matrix_world.to_translation()

    return abs(pos_obj.x - pos_cam.x)

def guardarDistancias(path):
 
    archivo_final = os.path.join(path, f"distancias_objetos_{i}.txt")

    if not os.path.exists(archivo_final):
        with open(archivo_final, "w") as f:
            f.write("objeto,distanciaReal,x_center,y_center,width,height\n")

    targets = ""

    # --- PROCESAR PUERTA ---
    if imprimirPuerta:
        bbox = get_bbox(puerta, scene, scene.camera)
        dist = calcular_distancia(puerta, scene.camera)
        # Separamos por comas e introducimos un salto de línea al final
        targets += f"puerta,{dist:.3f},{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}\n"

    # --- PROCESAR LLAVE ---
    if imprimirLlave:
        bbox = get_bbox(llave, scene, scene.camera)
        dist = calcular_distancia(llave, scene.camera)
        targets += f"llave,{dist:.3f},{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}\n"

    # --- PROCESAR QR ---
    if imprimirQR:
        bbox = get_bbox(interrogantes, scene, scene.camera)
        dist = calcular_distancia(interrogantes, scene.camera)
        targets += f"interrogacion,{dist:.3f},{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}\n"
    
    if targets != "":
        with open(archivo_final, "a") as f:
            f.write(targets)

