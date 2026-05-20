import bpy
import os
import random
import math

script_datos = bpy.data.texts["util"].as_string()
exec(script_datos)

setupCarpetas()


paredesH = bpy.data.collections.get("ParedesH").objects
nombres_paredesH = {o.name for o in paredesH} if paredesH else set()
pared_llave = bpy.data.objects.get("ParedLlave")

train = 60

random.seed(seed)
setupYOLO()

for i in range(train):
    generarMapa()
    guardarFrameYOLO(f"{ruta}/datasetH/real")
    print(f"Frame {i}. YOLO topdown")


random.seed(seed)
setupTopdown()

for i in range(train):
    generarMapa()
    guardarTopdown(f"{ruta}/datasetH/ground_truth")
    print(f"Frame {i}. Topdown")