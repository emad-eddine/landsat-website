import os
import requests
from usgs import api
import urllib.parse
import json
from landsatxplore.api import API
from .utils import *


def createSeason():

    apiLog = API(API_USERNAME, API_PASSWORD)
    API_KEY = api.login(API_USERNAME, API_PASSWORD)["data"]
    return apiLog,API_KEY


def searchForScene(apiLogin,lat,long,startData,endDate):
    scenes = apiLogin.search(
    dataset= API_DATASET,
    latitude=float(lat),
    longitude=float(long),
    start_date=startData,
    end_date= endDate,
    max_cloud_cover=MAX_CLOUD_COVER)

    return scenes

# we need to use LANDSAT8 L1
def getScenesWithL1(scenes):
    sceneId = []
    productId = []
    for s in scenes:
        id = str(s["display_id"])[ 0 : 7 ]
        if id == "LC08_L1": 
            sceneId.append(s["entity_id"]) 
            productId.append(s["landsat_product_id"])

    return sceneId,productId


def getDownloadOption(entity_id,API_KEY):
    downloadOptions = api.download_options(dataset=API_DATASET,
                                  entity_ids=entity_id,
                                  api_key=API_KEY)


    return downloadOptions




def getIDsForDownloadUrlForBand(bandsList,downloadOptions):

    bandsIds = {}

    for d1 in downloadOptions['data']:

        if d1["available"] == True:
            for d2 in d1["secondaryDownloads"]:
                if d2["available"] == True and d2["bulkAvailable"] == True :
                    bandName = str(d2["entityId"])
                    for band in bandsList :
                        comparedStr = str(band) + "_TIF"
                        if band != 10 or band!=11:
                            if bandName[-5:] == comparedStr :
                                bandsIds[band] = {"entityId":d2["entityId"],"productId":d2["id"]}
                        if band == 10 or band == 11:
                            if bandName[-6:] == comparedStr :
                                bandsIds[band] = {"entityId":d2["entityId"],"productId":d2["id"]}


    return bandsIds


def getDownloadUrl(bandsIds,API_KEY):
    url = api.download_request(
    dataset = API_DATASET,
    entity_id = bandsIds["entityId"],
    product_id = bandsIds["productId"],
    api_key=API_KEY
    )
    for d1 in url['data']["availableDownloads"]:
        downloadUrl = d1["url"]

    return downloadUrl


def logoutFromApi():
    api.logout()






    


