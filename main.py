import cv2 as cv
import numpy as np
import math
import json
from pathlib import Path
from tkinter import Tk     # from tkinter import Tk for Python 3.x
from tkinter.filedialog import askopenfilenames
import shutil
import os
import subprocess

#Adjustable Parameters
LAYERS = 255
GRID_SIZE = 1
LAYER_TIME = 1.5
#Calculated Values

match GRID_SIZE:
    case 1:
        cell_height = 5120
        cell_width = 9102
    case 2: 
        cell_height = 2520
        cell_width = 4480
    case 3: 
        cell_height = 1656
        cell_width = 2944
    case 4: 
        cell_height = 1224
        cell_width = 2176
    case 5: 
        cell_height = 1008
        cell_width = 1792
    case 6: 
        cell_height = 792
        cell_width = 1408
    case 7: 
        cell_height = 720
        cell_width = 1280
    case 8: 
        cell_height = 576
        cell_width = 1024
    case 9: 
        cell_height = 540
        cell_width = 960
    case _:
        cell_height = 5120
        cell_width = 9102

TOP_BOTTOM_SPACING = int((5120-(cell_height*GRID_SIZE))/(GRID_SIZE+1)/2)
LEFT_RIGHT_SPACING = int((9102-(cell_width*GRID_SIZE))/(GRID_SIZE+1)/2)

#Fixed Parameters
ASPECT_RATIO = 16/9

cwd = Path.cwd()

#Select Image
Tk().withdraw() # we don't want a full GUI, so keep the root window from appearing
imagenames = askopenfilenames(initialdir=cwd, title='Please Select Images') # show an "Open" dialog box and return the path to the selected file

file_count  = math.ceil(len(imagenames)/(GRID_SIZE**2))

image_list = []
for image in imagenames:

    #Open the image
    open_image = cv.imread(image, 0)
    height, width = open_image.shape

    #Crop to aspect ratio
    if (width/height) > (ASPECT_RATIO):
        cropped_width = (ASPECT_RATIO)*height
        spacing = int((width - cropped_width)/2)
        open_image = open_image[0:height, spacing:(width-spacing)]
    else:
        cropped_height = (1/ASPECT_RATIO)*width
        spacing = int((height - cropped_height)/2)
        open_image = open_image[spacing:(height-spacing), 0:width]
    
    #Resize to cell size
    open_image = cv.resize(open_image, (cell_width, cell_height), interpolation= cv.INTER_AREA)

    #Add white border
    open_image = cv.copyMakeBorder(open_image, top = TOP_BOTTOM_SPACING, bottom=TOP_BOTTOM_SPACING, left=LEFT_RIGHT_SPACING, right=LEFT_RIGHT_SPACING, borderType=cv.BORDER_CONSTANT, value=[255,255,255])
    image_list.append(open_image)

black = np.zeros((cell_height, cell_width, 1), dtype = "uint8")
black = cv.copyMakeBorder(black, top = TOP_BOTTOM_SPACING, bottom=TOP_BOTTOM_SPACING, left=LEFT_RIGHT_SPACING, right=LEFT_RIGHT_SPACING, borderType=cv.BORDER_CONSTANT, value=[255,255,255])

for i in range(GRID_SIZE**2 - len(image_list)%(GRID_SIZE**2)):
    image_list.append(black)

for c in range(0,file_count):
    combined_list = []
    for i in range(0,(GRID_SIZE**2),GRID_SIZE):
        sub_list = []
        for j in range(0,GRID_SIZE):
            sub_list.append(image_list[(c*GRID_SIZE**2)+i+j])
        combined_list.append(sub_list)
    combined_image = cv.vconcat([cv.hconcat(sub_list)  for sub_list in combined_list]) 
    combined_image = cv.copyMakeBorder(combined_image, top = TOP_BOTTOM_SPACING, bottom=TOP_BOTTOM_SPACING, left=LEFT_RIGHT_SPACING, right=LEFT_RIGHT_SPACING, borderType=cv.BORDER_CONSTANT, value=[255,255,255])
    combined_image = cv.resize(combined_image, (11520, 5120), interpolation=cv.INTER_CUBIC)
    combined_image = cv.flip(combined_image, 0)
    
    #Create File Structure
    first = Path(imagenames[c*GRID_SIZE**2]).stem 

    if ((c+1)*GRID_SIZE**2)-1 >= len(imagenames):
        last = "End"
    else:
        last = Path(imagenames[((c+1)*GRID_SIZE**2)-1]).stem
    first = ''.join(e for e in first if e.isalnum())
    last = ''.join(e for e in last if e.isalnum())
    stem = first + "_to_"  + last

    slicepath = cwd / stem / "slice"
    slicepath.mkdir(parents=True, exist_ok=True)
    previewpath = cwd / stem / "preview"
    previewpath.mkdir(parents=True, exist_ok=True)

    #Save Preview Images
    small_image = cv.resize(combined_image, (320, 180)) 
    cv.imwrite(str(previewpath / "huge.png"), combined_image)
    cv.imwrite(str(previewpath / "tiny.png"), small_image)

    #Save Sliced Images
    for count, value in enumerate(range(0,LAYERS+1)):
        ret, thresh = cv.threshold(combined_image, value,255, cv.THRESH_BINARY_INV)
        imagepath = slicepath / (str(count)+".png")
        cv.imwrite(str(imagepath), thresh)

    #Write JSON file
    size = {
        "X": 11520,
        "Y" :5120,
        "Millimeter":{"X": 218.88, "Y": 122.88},
        "Layers": LAYERS,
        "LayerHeight": 0.1
    }

    exposure = {
        "WaitTimeBeforeCure": 0,
        "LightOffTime": 0,
        "LightOnTime": LAYER_TIME,
        "LightPWM": 255,
        "WaitTimeAfterCure": 0,
        "LiftHeight": .001,
        "LiftSpeed": 1000,
        "LiftHeight2": .001,
        "LiftSpeed2": 1000,
        "WaitTimeAfterLift": 0,
        "RetractHeight": .001,
        "RetractSpeed": 1000,
        "RetractHeight2": .001,
        "RetractSpeed2": 1000
    }

    bottom = {
        "Count": 0,
        "WaitTimeBeforeCure": 0,
        "LightOffTime": 0,
        "LightOnTime": 0,
        "LightPWM": 255,
        "WaitTimeAfterCure": 0,
        "LiftHeight": 0,
        "LiftSpeed": 0,
        "LiftHeight2": 0,
        "LiftSpeed2": 0,
        "WaitTimeAfterLift": 0,
        "RetractHeight": 0,
        "RetractSpeed": 0,
        "RetractHeight2": 0,
        "RetractSpeed2": 0
    }

    layers = []

    for layer in range(0,LAYERS+1):
        layers.append({"Z": 0, "Exposure": exposure})

    properties = {"Size": size, "Exposure": exposure, "Bottom": bottom, "Vendor": {}, "AntiAliasLevel:": 8}

    with open((cwd / stem / "config.json"),"w") as file:
        file.write(json.dumps({"Properties":properties, "Layers:": layers}))

    #Sh(zip) it!
    zip_path = Path(shutil.make_archive(stem, 'zip', str(cwd / stem)))
    uvj_path = zip_path.rename(zip_path.with_suffix(".uvj"))
    # uvj_path = uvj_path.rename(cwd / "Output"/ (stem + ".ujv"))

    #Make it goo(ey)
    if (os.name == "nt"):
        subprocess.run("UVTools --cmd convert "+uvj_path.name+" goo")
        input("Process Done?:")
    else:
        os.system("./UVtools.AppImage --cmd convert "+uvj_path.name+ " goo")

    Path.unlink(uvj_path)
    shutil.rmtree(cwd / stem)
