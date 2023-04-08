from flask import Blueprint,Response,render_template,request,redirect,url_for,make_response,flash,jsonify
from flask_login import login_required,current_user
from .models import *
from werkzeug.utils import secure_filename
import os
from .lst import *
from usgs import api
from .utils import *
import json
from landsatxplore.api import API
import requests
import urllib.parse
from werkzeug.utils import secure_filename
from .apiHandler import *
import wget
from pathlib import Path
import re # regex
from threading import Thread
################### configuration

UPLOAD_FOLDER = 'website\\temp\\'
ALLOWED_EXTENSIONS = {'tif'}

view = Blueprint("view",__name__)
exporting_threads = {}

def page_not_found(e):
  return render_template('error.html'), 404


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

## variable for progressbar

message = None
progressMsg = None
progressCounter= None
isError = None

################# rendering pages
@view.route("/")
def goHome():
    return render_template("index.html",user = current_user)
@view.route("/heat")
@login_required
def goHeat():
    return render_template("heat.html",user = current_user)


################ create seprete thread for the process so we can be able to send progres

def simpleFormTask(simpleLocationName,simpleStudyDate,simpleStudyDateFrom,simpleStudyDateTo,TEMP_ID):
    
    global message 
    global progressMsg
    global progressCounter
    global isError 
    
    # api approche
    #print("simple approche")
    # first we need to get the location name,desired date and study profile
    message = ""
    progressMsg = "Connecter Au API...."
    progressCounter = 1
    isError = False
    lon = 0
    lat = 0

    #check if there is scenes with given infos
    # first we need to get API key will be valid for 1 hours and store it

    apiLogin = None
    API_KEY = None
    try:
        logoutFromApi()
        apiLogin,API_KEY = createSeason()
        print(API_KEY)
    except:
        isError = True
        message = "Erreur Clé API,essayer plus tard!"
    if API_KEY is not None:
        # proceded with finding the desired location
        # first we need to get the long and lat of the location
        if str(simpleLocationName) =="" or str(simpleLocationName) is None :
            logoutFromApi()
            isError = True
            message = "Aucune région été choisi!"
        else: 
            progressMsg = "Chercher la position geographique...."   
            address = simpleLocationName
            url = 'https://nominatim.openstreetmap.org/search/' + urllib.parse.quote(address) +'?format=json'
            try :
                response = requests.get(url).json()
                lat = float(response[0]["lat"])
                lon = float(response[0]["lon"])
                print(lat)
                print(lon)
            except:
                logoutFromApi()
                isError = True
                message = "Erreur lors la récuperation du position géographique!"

            # after we get location lets create time stamp    
            # ie 2023-03 => 2023-03-01 -> 2023-03-30
            try:
                startDate = simpleStudyDate + "-01"
                endDate = simpleStudyDate + "-30"
            except:
                logoutFromApi()
                isError = True
                message = "Erreur lors la récuperation du date d'étude!"
       
            # now lets search for the scene with LC08_L1 from 'display_id': 'LC09_L1TP_198035_20230326_20230326_02_T1'
            progressMsg = "Chercher les Scenes...." 
            progressCounter = 3
            scenes = searchForScene(apiLogin=apiLogin,
                                        lat=lat,
                                        long=lon,
                                        startData=startDate,
                                        endDate=endDate)
            
            levelOneSceneId = ""
            try:
                # in that case we need just one scene
                for s in scenes:
                    levelOneSceneId = checkSceneIsLevelOne(s)
                    if levelOneSceneId != "" or levelOneSceneId is not None:
                        break
                if levelOneSceneId == "" or levelOneSceneId is None:
                    logoutFromApi()
                    isError = True
                    message = "Aucune scene a été trouvé avec niveau 1!"
            except:
                logoutFromApi()
                isError = True
                message = "Aucune scene a été trouvé!"
            #print("simple scenes id ")
            #print(levelOneSceneId)
            # get download option for this scenes
            try :
                progressMsg = "Télécharger les bands du Scene...." 
                progressCounter = 4
                downloadOption = getDownloadOption(levelOneSceneId,API_KEY)

                # get the ids of bands so we can get the download link

                bandsIds = getIDsForDownloadUrlForBand(bandsList=BANDS_LIST,downloadOptions=downloadOption)
                #print(bandsIds)
                # get download urls for each band

                urls = getDownloadUrl(bandsIds=bandsIds,BAND_LIST=BANDS_LIST,API_KEY=API_KEY)

                #check if there is dir with user id if not lets  create one

                SAVE_FOLDER_PATH = os.path.join(UPLOAD_FOLDER, TEMP_ID)
                
                try:
                    if os.path.isdir(SAVE_FOLDER_PATH) == False:
                        os.mkdir(SAVE_FOLDER_PATH)
                except:
                    logoutFromApi()
                    isError = True
                    message = "Erreu lors creation votre reportoire,essayer plus tards!"

                # lets start the download and saving the .tif(s)
                try:
                    for b in BANDS_LIST:
                        FULL_PATH = str(SAVE_FOLDER_PATH) + "/" + str(b) + ".tif"
                        #wget.download(urls[b], FULL_PATH)
                        #print(urls[b])
                except:
                    logoutFromApi()
                    isError = True
                    message = "Erreur lors le téléchargement des Scenes!essayer plus tard!"

            except:
                logoutFromApi()
                isError = True
                message = "Aucune Lien de téléchargement a été trouvé!"

            # so far we should have all the bands we need to calculate LST
            # lets check if we got all the required bands
            # calculate LST
            progressMsg = "Calculer la temperature du surface du scene...." 
            progressCounter = 5

            BANDS_PATH = os.path.join(UPLOAD_FOLDER, TEMP_ID)
            isCalculated = __applyLST__(BANDS_PATH,TEMP_ID,"",simpleLocationName)

            if isCalculated == False:
                logoutFromApi()
                isError = True
                message = "Erreur il manque des fichier.tif!"
            #__applyLST__(BANDS_PATH,TEMP_ID)

            ##################### end of lst calculation ###################
            ##
            ##
            ##
            #############################################
            # after that lets handel the profile
            # after we get location lets create time stamp    
            # ie 2023-03 => 2023-03-01 -> 2023-03-30

            print("profile start handeling")
            progressMsg = "Générer les profiles...." 
            progressCounter = 6
            try:
                profileStartDate = simpleStudyDateFrom + "-01"
                profileEndDate = simpleStudyDateTo+ "-30"
                print(profileStartDate)
                print(profileEndDate)
            except:
                logoutFromApi()
                isError = True
                message = "Erreur lors la récuperation la date du profile d'étude!"


 
            # lets start serching for the scenes
            progressMsg = "Chercher les scenes du profile...." 
            scenes = searchForScene(apiLogin=apiLogin,
                                        lat=lat,
                                        long=lon,
                                        startData=profileStartDate,
                                        endDate=profileEndDate)
            levelOneSceneId =""
            levelOneSceneIdList = []
               
            # in that case we need all the scene L1
            try:
                for s in scenes:
                    levelOneSceneId,aquireDate = checkSceneIdsLevelOneForProfile(s)
                    if str(levelOneSceneId) !="" and str(aquireDate) !="":
                        obj = {"sceneId":levelOneSceneId,"date":aquireDate}
                        levelOneSceneIdList.append(obj)
                        #print(levelOneSceneId)
                
                if levelOneSceneIdList == False or levelOneSceneIdList is None:
                    logoutFromApi()
                    isError = True
                    message = "Aucune scenes a été trouve pour le profile et avec niveau 1!"
                                    
                #print(levelOneSceneIdList)
                    
            except:
                logoutFromApi()
                isError = True
                message = "Aucune scenes a éte trouvé pour le profle d'étude!"
            
            progressCounter = 8
            try :
                for sId in levelOneSceneIdList:
                    progressMsg = "Télécharger les images (peu prend du temps)...." 
                    # get download option for this scenes
                    downloadOption = getDownloadOption(sId["sceneId"],API_KEY)
                    #print("download options")

                    # get the ids of bands so we can get the download link
                    bandsIds = getIDsForDownloadUrlForBand(bandsList=BANDS_LIST,downloadOptions=downloadOption)
                    #print(bandsIds)


                    # get download urls for each band
                    urls = getDownloadUrl(bandsIds=bandsIds,BAND_LIST=BANDS_LIST,API_KEY=API_KEY)
                    #print(urls)
           
                    #check if there is dir with user id if not lets  create one

                    PARENT_SAVE_FOLDER_PATH = os.path.join(UPLOAD_FOLDER, TEMP_ID)
                    SAVE_FOLDER_PATH = os.path.join(PARENT_SAVE_FOLDER_PATH,sId["date"])
                    try:
                        #print("making dir ")
                        if os.path.isdir(SAVE_FOLDER_PATH) == False:
                            os.mkdir(SAVE_FOLDER_PATH)
                    except:
                        logoutFromApi()
                        isError = True
                        message = "Erreu lors creation votre reportoire,essayer plus tards!"

                    # lets start the download and saving the .tif(s)
                    try:
                        for b in BANDS_LIST:
                            FULL_PATH = str(SAVE_FOLDER_PATH) + "/" + str(b) + ".tif"
                            print(urls[b])
                            #wget.download(urls[b], FULL_PATH)  
                         

                        # let calculate the land surface temperature
                        try:
                            
                            progressMsg = "Calculer la temperature du surface...." 
                            folderName = sId["date"]
                            isCalculated = True

                            isCalculated = __applyLST__(SAVE_FOLDER_PATH,TEMP_ID,folderName,simpleLocationName)

                            if isCalculated == False:
                                logoutFromApi()
                                isError = True
                                message = "Erreur il manque des fichier.tif!"

                        except:
                            logoutFromApi()
                            isError = True
                            message = "Erreur lors calculer LST !essayer plus tard!"
                    except:
                        logoutFromApi()
                        isError = True
                        message = "Erreur lors le téléchargement les Scenes du profile!essayer plus tard!"

                progressMsg = "Terminer....."
                progressCounter = 10        
            except:
                logoutFromApi()
                isError = True
                message = "Aucune Lien de téléchargement a été trouvé!"
               
        ############# end of simple form #####################
        # 
        #  
        # #####################################################                 
    else :
        logoutFromApi()
        isError = True
        message = "Erreur Clé API,essayer plus tard!"
  

@view.route('/status', methods=['GET'])
def getStatus():
  statusList = {'msg':message,"error":isError,"pro":progressCounter,"proMsg":progressMsg}
  return json.dumps(statusList)

################## handling form sumbition
@view.route("/simpleForm",methods=['GET','POST'])
def simpleForme():
    if request.method == 'POST':
        TEMP_ID = str(current_user.get_id())
        simpleLocationName = request.form.get("slocation")
        simpleStudyDate = request.form.get("simpleStudyDate")
        simpleStudyDateFrom = request.form.get("simpleStudyDateFrom")
        simpleStudyDateTo = request.form.get("simpleStudyDateTo")
        t1 = Thread(target=simpleFormTask,args=(simpleLocationName,
                                        simpleStudyDate  ,
                                        simpleStudyDateFrom,
                                        simpleStudyDateTo,
                                        TEMP_ID))
        t1.start()

    return render_template("heat.html",user = current_user,check=True,adv=False)

######################################################################
#
#
#
#
#
#
#######################################################################
def advancedFormTask(advancedLocationName,advancedStudyDate,advancedStudyProfileFrom,advancedStudyProfileTo,TEMP_ID):
    
    global message 
    global progressMsg
    global progressCounter
    global isError

    message = ""

    progressCounter = 1
    isError = False

    if str(advancedLocationName) != "" and str(advancedStudyDate) != "" and str(advancedStudyProfileFrom) != "" and str(advancedStudyProfileTo) != "":
            
        progressMsg = "Vérifier la validité des images...."
        # check if file names match the patter ie bandNum.tif => 4.tif
        BANDS_PATH = os.path.join(UPLOAD_FOLDER, TEMP_ID)
            
        for file in os.listdir(BANDS_PATH):
            # check if current path is a file
            if os.path.isfile(os.path.join(BANDS_PATH, file)):
                fileNameWitoutExt = str(file)[:-4]

                isNumber = re.findall("[0-1][0-9]", fileNameWitoutExt)
                    
                if isNumber == False:
                    isError = True
                    message = "Les fichier exporter ont mauvaise notation"

            # at this point we got all required bands let calculate LST

            # #if all required bands are selected 4 5 10 11 continue
        progressMsg = "Calculer la temperature du surface...."
        progressCounter = 4
        __applyLST__(BANDS_PATH,TEMP_ID,"",advancedLocationName)

            #============end of lst calculation############            
            ###############################################
            #=======this section reserved for profile=====#
            
        progressMsg = "Génerer le profile...."
        progressCounter = 6
        profileStartDate = advancedStudyProfileFrom + "-01"
        profileEndDate = advancedStudyProfileTo+ "-30"
        print(profileStartDate)
        print(profileEndDate)
        
        lon = 0
        lat = 0

        #check if there is scenes with given infos
        # first we need to get API key will be valid for 1 hours and store it

        try:
            progressMsg = "Connexion au API...."
            logoutFromApi()
            apiLogin,API_KEY = createSeason()
            print(API_KEY)
        except:
            logoutFromApi()
            isError = True
            message = "Erreur Clé API,essayer plus tard!"
        if API_KEY is not None:
            # proceded with finding the desired location
            # first we need to get the long and lat of the location
            #   
            progressMsg = "Chercher la position geographique...." 
            address = advancedLocationName
            url = 'https://nominatim.openstreetmap.org/search/' + urllib.parse.quote(address) +'?format=json'
            try :
                response = requests.get(url).json()
                lat = float(response[0]["lat"])
                lon = float(response[0]["lon"])
                print(lat)
                print(lon)
            except:
                logoutFromApi()
                isError = True
                message = "Erreur lors la récuperation du position géographique!"
                
            progressMsg = "Chercher Les scenes...."
            # lets start serching for the scenes
            scenes = searchForScene(apiLogin=apiLogin,
                                        lat=lat,
                                        long=lon,
                                        startData=profileStartDate,
                                        endDate=profileEndDate)
            levelOneSceneId =""
            levelOneSceneIdList = []
               
                # in that case we need all the scene L1
            try:
                for s in scenes:
                    levelOneSceneId,aquireDate = checkSceneIdsLevelOneForProfile(s)
                    if str(levelOneSceneId) !="" and str(aquireDate) !="":
                        obj = {"sceneId":levelOneSceneId,"date":aquireDate}
                        levelOneSceneIdList.append(obj)
                    #print(levelOneSceneId)
                
                    if levelOneSceneIdList == False or levelOneSceneIdList is None:
                        logoutFromApi()
                        isError = True
                        message = "Aucune scenes a été trouve pour le profile et avec niveau 1!"
                        
                                    
                    print(levelOneSceneIdList)
                    
            except:
                logoutFromApi()
                isError = True
                message = "Aucune scenes a éte trouvé pour le profle d'étude!"
           
            try :
                progressCounter = 7
                for sId in levelOneSceneIdList:
                    progressMsg = "Chercher Lien de téléchargement...."
                    # get download option for this scenes
                    downloadOption = getDownloadOption(sId["sceneId"],API_KEY)
                    #print("download options")

                    # get the ids of bands so we can get the download link
                    bandsIds = getIDsForDownloadUrlForBand(bandsList=BANDS_LIST,downloadOptions=downloadOption)
                    #print(bandsIds)


                    # get download urls for each band
                    urls = getDownloadUrl(bandsIds=bandsIds,BAND_LIST=BANDS_LIST,API_KEY=API_KEY)
                    #print(urls)
           
                    #check if there is dir with user id if not lets  create one

                    PARENT_SAVE_FOLDER_PATH = os.path.join(UPLOAD_FOLDER, TEMP_ID)
                    SAVE_FOLDER_PATH = os.path.join(PARENT_SAVE_FOLDER_PATH,sId["date"])
                    try:
                        #print("making dir ")
                        if os.path.isdir(SAVE_FOLDER_PATH) == False:
                            os.mkdir(SAVE_FOLDER_PATH)
                    except:
                        logoutFromApi()
                        isError = True
                        message = "Erreu lors creation votre reportoire,essayer plus tards!"

                    # lets start the download and saving the .tif(s)
                    try:
                        progressMsg = "Télécherger les scenes...."
                        for b in BANDS_LIST:
                            FULL_PATH = str(SAVE_FOLDER_PATH) + "/" + str(b) + ".tif"
                            print(urls[b])
                            #wget.download(urls[b], FULL_PATH)                           
                        
                            # let calculate the land surface temperature
                            try:

                                folderName = sId["date"]
                                isCalculated = True
                                progressMsg = "Calculer la temperature du surface...."
                                isCalculated = __applyLST__(SAVE_FOLDER_PATH,TEMP_ID,folderName,advancedLocationName)
                                progressCounter = 8
                                if isCalculated == False:
                                    logoutFromApi()
                                    isError = True
                                    message = "Erreur il manque des fichier.tif!"

                            except:
                                logoutFromApi()
                                isError = True
                                message = "Erreur lors calculer LST !essayer plus tard!"

                    except:
                        logoutFromApi()
                        isError = True
                        message = "Erreur lors le téléchargement les Scenes du profile!essayer plus tard!"

                progressMsg = "Terminer...."
                progressCounter = 10
            except:
                logoutFromApi()
                isError = True
                message = "Aucune Lien de téléchargement a été trouvé!"
        else :
            isError = True
            message = "Erreur Clé API,essayer plus tard!"

    else:
        isError = True
        message = "Des champs sont vides"

        
@view.route('/statusAdv', methods=['GET'])
def getStatusAdv():
  statusList = {'msg':message,"error":isError,"pro":progressCounter,"proMsg":progressMsg}
  return json.dumps(statusList)

  
################## handling advanced form sumbition

@view.route("/advancedForm",methods=['GET','POST'])
def advancedForme():

    if request.method == 'POST':
        # get user form
        TEMP_ID = str(current_user.get_id())
        advancedLocationName = request.form.get("Alocation")
        advancedStudyDate = request.form.get("dateFrom")
        advancedStudyProfileFrom = request.form.get("advancedStudyDateFrom")
        advancedStudyProfileTo = request.form.get("advancedStudyDateTo")

        t1 = Thread(target=advancedFormTask,args=(advancedLocationName,
                                        advancedStudyDate  ,
                                        advancedStudyProfileFrom,
                                        advancedStudyProfileTo,
                                        TEMP_ID))
        t1.start()

    return render_template("heat.html",user = current_user,check=False,adv=True)

        


############# end form handling functions ####################


##########this function will handel files upload post request
@view.route("/upload",methods=['GET','POST'])
@login_required
def upload():

    if request.method == 'POST':
        #print("upload")
        #get file chuncks
        file = request.files["file"]
        file_uuid = request.form["dzuuid"]
        # Generate a unique filename to avoid overwriting using 8 chars of uuid before filename.
        filename = f"{file_uuid[:8]}_{secure_filename(file.filename)}"
        
        # check if unique dir exist if not we create one
        user = current_user
        TEMP_ID = str(user.get_id())
        SAVE_FOLDER_PATH = os.path.join(UPLOAD_FOLDER, TEMP_ID)

        if os.path.isdir(SAVE_FOLDER_PATH) == False:
            os.mkdir(SAVE_FOLDER_PATH)

        # collect the chunks in one file
        save_path = Path(SAVE_FOLDER_PATH, filename)
        current_chunk = int(request.form["dzchunkindex"])
        try:
            with open(save_path, "ab") as f:
                f.seek(int(request.form["dzchunkbyteoffset"]))
                f.write(file.stream.read())
        except OSError:
            return "Error saving file.", 500
        # some error handling

        total_chunks = int(request.form["dztotalchunkcount"])

        # Add 1 since current_chunk is zero-indexed
        if current_chunk + 1 == total_chunks:
            # This was the last chunk, the file should be complete and the size we expect
            if os.path.getsize(save_path) != int(request.form["dztotalfilesize"]):
                return "Size mismatch.", 500
            
    

    return render_template("heat.html",user = current_user)


######## this function will handel LST Traitment ########


def calcLST_SC(bands):

    BAND_4 = bands[4]
    BAND_5 = bands[5]
    BAND_10 = bands[10]
    BAND_11 = bands[11]

    # crop the bands before calculation
    # crop according to shapefile

    TOA_10,TOA_11 = calculatesTOA(BAND_10,BAND_11)
    BT_10,BT_11 = calculateBT(TOA_10,TOA_11)
    NDVI = calculateNDVI(BAND_4,BAND_5)
    PV = calculatePV(NDVI)
    E = calculateEM(PV)
    LST_signleChannel_B10= calculateLSTSignalChannel(BT_10,E)
    LST_signleChannel_B11= calculateLSTSignalChannel(BT_11,E)

    return LST_signleChannel_B10,LST_signleChannel_B11


def __applyLST__(BANDS_PATH,serveFolderId,serverFolderDate,locationName):

    bands,isFull = getBands(BANDS_PATH,BANDS_LIST)

    # #if all required bands are selected 4 5 10 11 continue

    if isFull == True :
        # Calculate LST 
        try :
            LST_B10,LST_B11 = calcLST_SC(bands)

            SAVE_PATH_B10 = os.path.join(BANDS_PATH,"pre_result_10.tif")
            SAVE_PATH_B11 = os.path.join(BANDS_PATH,"pre_result_11.tif")

            # pre save the tifs

            saveLSTInTif(imagery=bands[10],lst=LST_B10,path=SAVE_PATH_B10)
            saveLSTInTif(imagery=bands[10],lst=LST_B11,path=SAVE_PATH_B11)

            isShapeCreated,shapePath = getWilayaShapeFile(locationName=locationName,outputFolder=BANDS_PATH)

            if isShapeCreated == True:
                # if shapefile is created crop the bands
                projectShapePath = os.path.join(BANDS_PATH,"pro.shp")

                isProjectedCreated = createShapeFileProjection(shapeFilePath=shapePath,
                                                       projectShapePath=projectShapePath,
                                                       bandPath=SAVE_PATH_B10)


                if isProjectedCreated == True:

                    savingPath = os.path.join(BANDS_PATH,"clip_10.tif")

                    croped = cropRaster(projectShapePath=projectShapePath,
                                    bandPath=SAVE_PATH_B10,bandOutputBand=savingPath)
                    print(croped) 
                    if croped == True:

                        # convert the result to EPSG:4326
                        RESULT_BATH = "C:\Apache24\htdocs"
                        SAVE_FOLDER_PATH1 = os.path.join(RESULT_BATH, serveFolderId)
                        SAVE_FOLDER_PATH2 = os.path.join(SAVE_FOLDER_PATH1, serverFolderDate)
                        try:
                            if os.path.isdir(SAVE_FOLDER_PATH1) == False:
                                os.mkdir(SAVE_FOLDER_PATH1)

                            if os.path.isdir(SAVE_FOLDER_PATH2) == False:
                                os.mkdir(SAVE_FOLDER_PATH2)
                        except:
                            return render_template("heat.html",user = current_user,ErrorMsg="",aErrorMsg="Erreur lors Créer la résultat! Essayer plus tards")
                    
                        OUTPUT_PATH_B10 = os.path.join(SAVE_FOLDER_PATH2,"r_10.tif")
                        OUTPUT_PATH_B11 = os.path.join(SAVE_FOLDER_PATH2,"r_11.tif")

                        changeProjection(lstPath=savingPath,outputPath=OUTPUT_PATH_B10)
                        changeProjection(lstPath=SAVE_PATH_B11,outputPath=OUTPUT_PATH_B11)


            ### delete the temp folder

        except:
            return False

    else:
        return False 
        


######################################################################
# 
# 
# Visualisation section
# 
####################################################################### 
@view.route("/board")
@login_required
def goBoard():


    user = current_user
    TEMP_ID = str(user.get_id())
    LST_TIF_LINK = "http://localhost:8080/" + TEMP_ID + "/r_10.tif"
    print(LST_TIF_LINK)
    return render_template("dashboard.html",user = current_user,LST_TIF_LINK=LST_TIF_LINK)

@view.route("/profile",methods=['GET','POST'])
def processProfile():
    #get the dir name of profile save it as a list for label
    #get from each dir result lst and read as array
    #get the value at position send from js
    #save the values in a list
    if request.method == 'POST':
        # api approche
        #print("simple approche")
        # first we need to get the location name,desired date and study profile
        data = request.form
        #print(request.form)
        #first lets get the lan and lng

        lat = data.getlist('lat')
        lng = data.getlist('lon')
        lat = lat[0]
        lng = lng[0]
        
        print(lat)
        print(lng)

        #let prepare the variable that we need

        labels = [] # this will x axis represent date
        band10Data = [] # these data for y axis reprent temp


        #let get all the bands in server dir

        user = current_user
        ID = str(user.get_id())
        SERVER_PATH = "C:\Apache24\htdocs"
        SERVER_PATH = os.path.join(SERVER_PATH,ID)

        for root, dirs, files in os.walk(SERVER_PATH):
            for d in dirs:
                labels.append(d)
                print(d)


                #get the tif file for band 10,11
                band10_tif = os.path.join(root, d,"r_10.tif")
                band11_tif = os.path.join(root, d,"r_10.tif")
                #print(band10_tif)

                band10Value = getPixelValue(band10_tif,lat,lng)
                #band11Value = getPixelValue(band11_tif,lat,lng)
                band10Data.append(band10Value)
                #band11Data.append(band11Value)
                #print(band10Value)

                   


        # print(labels)
        # print(band10Data)
        # print(band11Data)

        responseObj = {"labels":labels,
                       "band10":band10Data}


        return jsonify(responseObj)

