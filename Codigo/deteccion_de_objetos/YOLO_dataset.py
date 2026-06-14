import bpy
import os
import random
import math

script_datos = bpy.data.texts["util"].as_string()
exec(script_datos)
setupCarpetas()


train = 1000
val = 250
test = 75


generarMapa()
random.seed(seed)
setupYOLO()
for i in range(train):
    generarMapa()
    guardarFrameYOLO(f"{ruta}/dataset/train/images")
    guardarLabelYOLO(f"{ruta}/dataset/train/labels")
    print(f"Train. Imagen: {i}")
    
 
for i in range(val):
    generarMapa()
    guardarFrameYOLO(f"{ruta}/dataset/val/images")
    guardarLabelYOLO(f"{ruta}/dataset/val/labels")
    print(f"Val. Imagen: {i}")
    

for i in range(test):
    generarMapa()
    guardarFrameYOLO(f"{ruta}/dataset/test/images")
    guardarLabelYOLO(f"{ruta}/dataset/test/labels")
    print(f"Test. Imagen: {i}")
