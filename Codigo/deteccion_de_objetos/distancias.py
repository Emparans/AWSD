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
    bpy.context.view_layer.update()
    guardarDistancias(f"{ruta}/dataset/train/distancias")
    print(f"Train distancias. Imagen: {i}")
    
 
for i in range(val):
    generarMapa()
    print(f"Val. Imagen: {i}")
    
for i in range(test):
    generarMapa()
    bpy.context.view_layer.update()
    guardarDistancias(f"{ruta}/dataset/test/distancias")
    print(f"Test distancias. Imagen: {i}")

