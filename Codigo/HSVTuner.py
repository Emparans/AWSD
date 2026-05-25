import cv2
import numpy as np
from pathlib import Path

def nothing(x):
    pass

# Load your REAL image here

imgName = "PrimeraCasilla"
input_path = f"{Path(__file__).parent}/testOutput/{imgName}_resized.jpg"

img = cv2.imread(input_path)
if img is None:
    print(f"No se pudo cargar la imagen en {input_path}")
    exit()

img = cv2.resize(img, (800, 600))
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

cv2.namedWindow('HSV Tuner')

# Create trackbars for color change
cv2.createTrackbar('HMin', 'HSV Tuner', 0, 179, nothing)
cv2.createTrackbar('SMin', 'HSV Tuner', 0, 255, nothing)
cv2.createTrackbar('VMin', 'HSV Tuner', 0, 255, nothing)
cv2.createTrackbar('HMax', 'HSV Tuner', 179, 179, nothing)
cv2.createTrackbar('SMax', 'HSV Tuner', 255, 255, nothing)
cv2.createTrackbar('VMax', 'HSV Tuner', 255, 255, nothing)

# Set default values for Max HSV
cv2.setTrackbarPos('HMax', 'HSV Tuner', 179)
cv2.setTrackbarPos('SMax', 'HSV Tuner', 255)
cv2.setTrackbarPos('VMax', 'HSV Tuner', 255)

while True:
    hMin = cv2.getTrackbarPos('HMin', 'HSV Tuner')
    sMin = cv2.getTrackbarPos('SMin', 'HSV Tuner')
    vMin = cv2.getTrackbarPos('VMin', 'HSV Tuner')
    hMax = cv2.getTrackbarPos('HMax', 'HSV Tuner')
    sMax = cv2.getTrackbarPos('SMax', 'HSV Tuner')
    vMax = cv2.getTrackbarPos('VMax', 'HSV Tuner')

    lower = np.array([hMin, sMin, vMin])
    upper = np.array([hMax, sMax, vMax])

    mask = cv2.inRange(hsv, lower, upper)
    result = cv2.bitwise_and(img, img, mask=mask)

    cv2.imshow('HSV Tuner', mask)
    cv2.imshow('Mask', mask)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        print(f"New Lower: [{hMin}, {sMin}, {vMin}]")
        print(f"New Upper: [{hMax}, {sMax}, {vMax}]")
        break

cv2.destroyAllWindows()