import bpy
import os
import random
import math

from bpy_extras.object_utils import world_to_camera_view

def get_bbox(obj, scene, cam):
    mat = obj.matrix_world
    nodes = [world_to_camera_view(scene, cam, mat @ v.co) for v in obj.data.vertices]
    
    x_coords = [n.x for n in nodes]
    y_coords = [n.y for n in nodes]
    
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
    carpetas_yolo = [
        os.path.join(rutaOutput, "train", "images"),
        os.path.join(rutaOutput, "train", "labels"),
        os.path.join(rutaOutput, "val", "images"),
        os.path.join(rutaOutput, "val", "labels")
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
    offset = random.randint(0,3)
    posicionX = 11 - (offset*2)
    centro.location = (posicionX,0,0)
    return offset
        
def moverPuerta(puerta, offsetLlave):
    offset = random.randint(0,3)

    fixedOffset = max(0,min(offset + offsetLlave,3))
    posicionX = 10 - (fixedOffset*2)
    puerta.location = (posicionX,0,0.01)
    return offset

def moverCamara(cam):
    cam.location = (0.5,random.uniform(-1,1) / 10, 1.2 + (random.uniform(-1,1) / 10))
    
    x = math.radians(90 + random.uniform(-1,1))
    y = math.radians(random.uniform(-1,1))
    z = math.radians(-90 + random.uniform(-5,5))
    cam.rotation_euler = (math.radians(90),0,math.radians(-90))
    #cam.rotation_euler = (x, y, z)

def cambiarLuz(luz):
    luz.data.energy = random.uniform(0,80)
    luz.rotation_euler[2] = random.uniform(0, 2 * math.pi)
    luz.rotation_euler[0] = math.radians(random.uniform(-70, 70))


def cambiarTextura(objeto):
    mat = objeto.active_material
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    
    
    #cambiar textura
    tex_node = next((n for n in nodes if n.type == 'TEX_IMAGE'), None)
    if tex_node:
        id = random.randint(0,3)
        img = clases[id]
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


def guardarFrame(i, folder):
    
    scene = bpy.context.scene
    scene.render.filepath = os.path.join(rutaOutput+folder+"/images", f"img_{i}.png")
    bpy.ops.render.render(write_still=True)


    targets = ""
    if imprimirPuerta:
        bbox = get_bbox(puerta, scene, scene.camera)
        targets += f"{clasePuerta} {bbox[0]} {bbox[1]} {bbox[2]} {bbox[3]}\n"
          
    if imprimirLlave:
        bbox = get_bbox(llave, scene, scene.camera)
        targets += f"{claseLlave} {bbox[0]} {bbox[1]} {bbox[2]} {bbox[3]}"   

    with open(os.path.join(rutaOutput+folder+"/labels", f"img_{i}.txt"), 'w') as f:
        f.write(targets)



def generarMapa():
    global imprimirPuerta, imprimirLlave, clasePuerta, claseLlave
    cambiarParedes(paredes)
    llaveX = moverLlave(centroLlave)
    puertaX = moverPuerta(puerta, llaveX)

    clasePuerta = cambiarTextura(puerta)
    claseLlave = cambiarTextura(llave)
    
    cambiarLuz(luz)
    
    moverCamara(camara)
    
    tipo = random.randint(0,2)
    print(tipo)
    match tipo:
        case 0:
            imprimirPuerta = False
            esconder(puerta)
            imprimirLlave = True
            mostrar(llave)
            mostrar(soporte)
        case 1:
            imprimirPuerta = True
            mostrar(puerta)
            imprimirLlave = False
            esconder(llave)
            esconder(soporte)
        case 2:
            imprimirPuerta = True
            mostrar(puerta)
            imprimirLlave = True
            mostrar(llave)
            mostrar(soporte)
    
    
    


#variables
rutaTexturas = "C:/Users/jempa/Desktop/h/Texturas/"
rutaOutput = "C:/Users/jempa/Desktop/h/dataset"
paredes = bpy.data.collections.get("ParedesClave").objects
puerta = bpy.data.objects["Puerta"]
centroLlave = bpy.data.objects["Centro"]
llave = bpy.data.objects["Llave"]
soporte = bpy.data.objects["Soporte"]
camara = bpy.data.objects["camara"]
luz = bpy.data.objects["Luz"]
imprimirPuerta = False
imprimirLlave = False
clasePuerta = -1
claseLlave = -1

train = 200
val = 50


clases = ["estrella","luna","nube","sol"]

setupCarpetas()

for i in range(train):
    generarMapa()
    guardarFrame(i, "/train")
    print(f"Train. Imagen: {i}")
    
    
for i in range(val):
    generarMapa()
    guardarFrame(i, "/val")
    print(f"Test. Imagen: {i}")
