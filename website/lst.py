# import all the required libaries
from .utils import PROJ_DB_PATH
import os
os.environ['PROJ_LIB'] = PROJ_DB_PATH
import rasterio
from rasterio import plot
import matplotlib.pyplot as plt
from PIL import Image
import numpy as np
import math
from osgeo import gdal
from rasterio.windows import Window
import geopandas as gpd
import pandas as pd
import fiona
import rasterio.mask
from .utils import SHAPEFILE_PATH

############## LST SECTION ##############################

##### before start process iterate the temp dir and return needed bands

# this function get desired bands from dir given a list contain desired bands number

# for the LST we need band 4,5,10,11

def getBands(bandsDir,bandNum):
       
    # iterate the dir to get all the bands files in it .tif
    
    filesNamesList = []
    bands = {}

    isFull = False
    for file in os.listdir(bandsDir):
        
    # check if current path is a file
        if os.path.isfile(os.path.join(bandsDir, file)):
                 
            fileNameWitoutExt = str(file)[:-4]
                
            for num in bandNum :
                if num < 10 and num > 0 :
                    if fileNameWitoutExt[-1] == str(num) :
                        bands[num] = str(bandsDir) + "\\" + str(file)
                          
                  
                elif num == 10 :
                    if fileNameWitoutExt[-1] == "0" and fileNameWitoutExt[-2] == "1" :
                        bands[num] = str(bandsDir) + "\\" + str(file)
                       
                elif num == 11 :
                    if fileNameWitoutExt[-1] == "1" and fileNameWitoutExt[-2] == "1" :
                        bands[num] = str(bandsDir) + "\\" + str(file)
                            
    if len(bands) == len(bandNum) :
        isFull = True
    else:
        isFull = False                     
    
    return  bands,isFull

# this function get the path of a specific ban

# def getBandPath(bandsList,bandNum):

#     for file in bandsList:

#         fileNameWitoutExt = str(file)[:-4]

#         if fileNameWitoutExt[-1] == str(bandNum):
#             return file
#     pass  



# first step calculate TOA (radiance)
# function that calculate the TOA (Top of Atmospheric)

# |=====TOA (L) = ML * Qcal + AL =====|
# ML = Band-specific multiplicative rescaling factor from the metadata (RADIANCE_MULT_BAND_x, where x is the band number).
# Qcal = corresponds to band 10.
# AL = Band-specific additive rescaling factor from the metadata (RADIANCE_ADD_BAND_x, where x is the band number).
# ML = 3.3420E-04
# AL = 0.1

def calculatesTOA(band10Path,band11Path):
    
    # open .tif bands
    band10 = rasterio.open(band10Path)
    band11 = rasterio.open(band11Path)

    #convert bands for math operation
    Qcal10 = band10.read(1)
    Qcal11=  band11.read(1)

    #calculate TOA
    TOA_10 = 3.3420*10**-4*Qcal10 + 0.1
    TOA_11 = 3.3420*10**-4*Qcal11 + 0.1
    
    return TOA_10,TOA_11


# second step calculate BT (Brightness temperature)
# BT = (K2 / (ln (K1 / L) + 1)) - 273.15
# where:
# K1 = Band-specific thermal conversion constant from the metadata (K1_CONSTANT_BAND_x, where x is the thermal band number).
# K2 = Band-specific thermal conversion constant from the metadata (K2_CONSTANT_BAND_x, where x is the thermal band number).
# L = TOA
# − 273.15 for result in C°

def calculateBT(TOA_10,TOA_11):
    
    BT_10 = (1321.0789/(np.log(774.8853/TOA_10 + 1))) - 273.15

    BT_11 = (1321.0789/(np.log(774.8853/TOA_11 + 1))) - 273.15
    
    return BT_10,BT_11



# step 3 calculate the ndvi
# NDVI = (Band 5 – Band 4) / (Band 5 + Band 4)
# NDVI = (red - nir) / (red + nir)

def calculateNDVI(band4Path,band5Path):
    
    #open and read band 4 red
    band4 = rasterio.open(band4Path)
    red = band4.read(1)
    
    # open and read band 5 nir
    band5 = rasterio.open(band5Path)
    nir = band5.read(1)
    
    # calculate ndvi
    
    NDVI = (red-nir)/(red + nir)
    return NDVI

# 4 step calculate 
# 1° proportion de végétation P_V 
# PV=((NDVI - NDVImin) / nDVImax - NDVImin)^2
# minNDVI = 0.2 (Ref. Sobrino et al. 2004)
# maxNDVI = 0.5 (Ref. Sobrino et al. 2004)

def calculatePV(ndvi):
    
    minNDVI = 0.2
    maxNDVI = 0.5
    PV= ((ndvi - minNDVI)/(maxNDVI - minNDVI))**2
    
    return PV

# 5 step calculate surface Emissivity e 
# ε=0.004*PV+0.986 

def calculateEM(PV):
    
    E = 0.004*PV+0.986
    
    return E

# caluclate lst using signal channel algorithm
# LST = BT / ((1+(10.8*(BT/14380))*ln(E)))

def calculateLSTSignalChannel(BT,E):
    
    a = 10.8 * (BT/14380)
    b = a * np.log(E)
    c = 1 + b

    LST = BT / c
    
    return LST

# show lst map for test purpose

def showLSTMap(LST):
    
    # show the temperatur only from 0 C°
    lst = LST>=0
    x=LST*lst
    x.min()
    
    plt.imshow(x, cmap='jet')
    plt.colorbar()

#############################################

################ Mono windows algorithme ###############


# constants
To= 26
To_K= To + 273.15
RH=42
tau = 0
RH_fraction= RH/100

# calculate Emissivity according to  Van de Griend and Owe 1993
# EV = 1.094 + 0.047*np.log(NDVI)

def calculateE_Van(ndvi):
    
    E = 1.094 + 0.047*np.log(ndvi)
    
    return E


#' Atmospheric transmittance calculation

def calculateAT() :
    
    
    W= 0.0981*10*0.6108**((17.27*(To_K-273.15))/ (237.3+(To_K-273.15)))*RH_fraction+0.1697

    tau = -0.0164*W**2-0.04203*W+0.9715
    
    return tau

##' Mean atmospheric temperature

def MAT (To, mod):
    To_K= To + 273.15
    if  mod == "USA 1976 Standard": 
        Ta = 25.940 + 0.8805*To_K
    elif mod == "Tropical Region":
        Ta = 17.977 + 0.9172*To_K
    elif mod == "Mid-latitude Summer Region":
        Ta = 16.011 + 0.9262*To_K
    else:
        Ta = 19.270 + 0.9112*To_K
    return Ta


# caluclate lst

def calculateLSTMonoWindow(bt, tau, EV, Ta):
    
    C= EV*tau
    D= (1-tau)*(1+(1-EV)*tau)
    LST_mwa = (-67.355351*(1-C-D)+(0.458606*(1-C-D)+C+D)*bt-D*Ta)/C
    
    return LST_mwa


### saving the result



def saveLSTInTif(imagery,lst,path):

    # remove the nan value from 2array (lst)
    for i in range(lst.shape[0]):
        for j in range(lst.shape[1]):
            if math.isnan(lst[i][j]) == True:
                lst[i][j] = 0

    # read the image

    imagery = rasterio.open(imagery)

    # transform
    t = rasterio.transform.from_bounds(*imagery.bounds,lst.shape[0],lst.shape[1])

    # write the data
    new_dataset = rasterio.open(path, 'w', driver='GTiff',
                            height = lst.shape[1], width = lst.shape[0],
                            count=1, dtype=str(lst.dtype),
                            crs=imagery.crs,
                            transform=t
                            )

    new_dataset.write(lst,1)
    new_dataset.close()



## this function will transform the projection of tif file to EPSG:4326

def changeProjection(lstPath,outputPath):

    input_raster = gdal.Open(lstPath)
    warp = gdal.Warp(outputPath,input_raster,dstSRS='EPSG:4326')


########################################################################

#### this function will get pixel value from tif using lan and lng

def getPixelValue(BandFile,lat,lng):

    with rasterio.open(BandFile) as f:
        # Load metadata
        meta = f.meta
    
        # My target coordinates
        x_coord = float(lng) #lng
        y_coord = float(lat) #lat
    
        # Use the transform in the metadata and your coordinates
        rowcol = rasterio.transform.rowcol(meta['transform'], xs=x_coord, ys=y_coord)

        # rowcol value: ex (977994, 978126)

        y = rowcol[0]
        x = rowcol[1]

        # Load specific pixel only using a window
        window = Window(x,y,1,1)
        arr = f.read(window=window)
        value = arr[0][0][0]

    return value


##########################################################"
# this function will get the shapefile of selected wilaya

def getWilayaShapeFile(locationName,outputFolder):
    
    try:
        # get the shapeFile
        df = gpd.read_file(SHAPEFILE_PATH)

        index = str(locationName).capitalize()
        for i in range(len(df.ID_0)):
            if(index != df.NAME_1[i]):
                df = df.drop(i)

        # save the output

        fileName = locationName + ".shp"
        path = os.path.join(outputFolder,fileName )
        df.to_file(path, driver='ESRI Shapefile')
    except:
        return False
    return True,path


##########################################################


# this function will create a shapefile based on image projectopn

def createShapeFileProjection(shapeFilePath,projectShapePath,bandPath):

    try:

    # Read shape file (created by Las Bound) using geopandas
        shpFile = gpd.read_file(shapeFilePath)

    # Read imagery file downloaded from national map
        imagery = rasterio.open(bandPath)

    #project shapefile to imagery

        shpFile  = shpFile.to_crs(imagery.crs)

    # save the new shapefile

        shpFile.to_file(projectShapePath, driver='ESRI Shapefile')
    except:
        return False
    
    return True

# this function will crop raster according to shapefile

def cropRaster(projectShapePath,bandPath,bandOutputBand):

    # crop the band
    try:
        with fiona.open(projectShapePath, "r") as shapefile:
            shapes = [feature["geometry"] for feature in shapefile]

        with rasterio.open(bandPath) as src:

            out_image, out_transform = rasterio.mask.mask(src, shapes, crop=True)
            out_meta = src.meta

        out_meta.update({"driver": "GTiff",
                 "height": out_image.shape[1],
                 "width": out_image.shape[2],
                 "transform": out_transform})


        with rasterio.open(bandOutputBand, "w", **out_meta) as dest:
            dest.write(out_image)

    except:
        return False
    
    return True


    

