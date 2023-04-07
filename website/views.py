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

################# rendering pages
@view.route("/")
def goHome():
    return render_template("index.html",user = current_user)
@view.route("/heat")
@login_required
def goHeat():
    return render_template("heat.html",user = current_user)


################## handling form sumbition
@view.route("/simpleForm",methods=['GET','POST'])
def simpleForme():
    if request.method == 'POST':
        # api approche
        #print("simple approche")
        # first we need to get the location name,desired date and study profile
        simpleLocationName = request.form.get("slocation")
        simpleStudyDate = request.form.get("simpleStudyDate")
        simpleStudyDateFrom = request.form.get("simpleStudyDateFrom")
        simpleStudyDateTo = request.form.get("simpleStudyDateTo")


        lon = 0
        lat = 0

        #check if there is scenes with given infos
        # first we need to get API key will be valid for 1 hours and store it

        try:
            logoutFromApi()
            apiLogin,API_KEY = createSeason()
            print(API_KEY)
        except:
            return render_template("heat.html",user = current_user,ErrorMsg = "Erreur Clé API,essayer plus tard!")
        if API_KEY is not None:
                # proceded with finding the desired location
                # first we need to get the long and lat of the location
            if str(simpleLocationName) =="" or str(simpleLocationName) is None :
                 logoutFromApi()
                 return render_template("heat.html",user = current_user,ErrorMsg = "Aucune région été choisi!")
            else:    
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
                    return render_template("heat.html",user = current_user,ErrorMsg = "Erreur lors la récuperation du position géographique!")

            # after we get location lets create time stamp    
            # ie 2023-03 => 2023-03-01 -> 2023-03-30
            try:
                startDate = simpleStudyDate + "-01"
                endDate = simpleStudyDate + "-30"
            except:
                logoutFromApi()
                return render_template("heat.html",user = current_user,ErrorMsg = "Erreur lors la récuperation du date d'étude!")
            
            
            # now lets search for the scene with LC08_L1 from 'display_id': 'LC09_L1TP_198035_20230326_20230326_02_T1'
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
                    return render_template("heat.html",user = current_user,ErrorMsg = "Aucune scene a été trouvé avec niveau 1!")
            except:
                return render_template("heat.html",user = current_user,ErrorMsg = "Aucune scene a été trouvé!")
            #print("simple scenes id ")
            #print(levelOneSceneId)
            # get download option for this scenes
            try :
                downloadOption = getDownloadOption(levelOneSceneId,API_KEY)

            # get the ids of bands so we can get the download link

                bandsIds = getIDsForDownloadUrlForBand(bandsList=BANDS_LIST,downloadOptions=downloadOption)
                #print(bandsIds)
            # get download urls for each band

                urls = getDownloadUrl(bandsIds=bandsIds,BAND_LIST=BANDS_LIST,API_KEY=API_KEY)

                #check if there is dir with user id if not lets  create one
                userUsed = current_user
                TEMP_ID = str(userUsed.get_id())
                SAVE_FOLDER_PATH = os.path.join(UPLOAD_FOLDER, TEMP_ID)
                
                try:
                    if os.path.isdir(SAVE_FOLDER_PATH) == False:
                        os.mkdir(SAVE_FOLDER_PATH)
                except:
                    logoutFromApi()
                    return render_template("heat.html",user = current_user,ErrorMsg = "Erreu lors creation votre reportoire,essayer plus tards!")

                # lets start the download and saving the .tif(s)
                try:
                    for b in BANDS_LIST:
                        FULL_PATH = str(SAVE_FOLDER_PATH) + "/" + str(b) + ".tif"
                        #wget.download(urls[b], FULL_PATH)
                        #print(urls[b])
                except:
                    logoutFromApi()
                    return render_template("heat.html",user = current_user,ErrorMsg = "Erreur lors le téléchargement des Scenes!essayer plus tard!")
            except:
                logoutFromApi()
                return render_template("heat.html",user = current_user,ErrorMsg = "Aucune Lien de téléchargement a été trouvé!")

            # so far we should have all the bands we need to calculate LST
            # lets check if we got all the required bands
            # calculate LST
            user = current_user
            TEMP_ID = str(user.get_id())
            BANDS_PATH = os.path.join(UPLOAD_FOLDER, TEMP_ID)
            isCalculated = __applyLST__(BANDS_PATH,TEMP_ID,"")

            if isCalculated == False:
                logoutFromApi()
                return render_template("heat.html",user = current_user,ErrorMsg = "Erreur il manque des fichier.tif!")
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
            try:
                profileStartDate = simpleStudyDateFrom + "-01"
                profileEndDate = simpleStudyDateTo+ "-30"
                print(profileStartDate)
                print(profileEndDate)
            except:
                logoutFromApi()
                return render_template("heat.html",user = current_user,ErrorMsg = "Erreur lors la récuperation la date du profile d'étude!")


 
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
                    return render_template("heat.html",user = current_user,ErrorMsg = "Aucune scenes a été trouve pour le profile et avec niveau 1!")
                                    
                #print(levelOneSceneIdList)
                    
            except:
                logoutFromApi()
                return render_template("heat.html",user = current_user,ErrorMsg = "Aucune scenes a éte trouvé pour le profle d'étude!")
           
            try :
                for sId in levelOneSceneIdList:
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
                    userUsed = current_user
                    TEMP_ID = str(userUsed.get_id())
                    PARENT_SAVE_FOLDER_PATH = os.path.join(UPLOAD_FOLDER, TEMP_ID)
                    SAVE_FOLDER_PATH = os.path.join(PARENT_SAVE_FOLDER_PATH,sId["date"])
                    try:
                        #print("making dir ")
                        if os.path.isdir(SAVE_FOLDER_PATH) == False:
                            os.mkdir(SAVE_FOLDER_PATH)
                    except:
                        logoutFromApi()
                        return render_template("heat.html",user = current_user,ErrorMsg = "Erreu lors creation votre reportoire,essayer plus tards!")

                    # lets start the download and saving the .tif(s)
                    try:
                        for b in BANDS_LIST:
                            FULL_PATH = str(SAVE_FOLDER_PATH) + "/" + str(b) + ".tif"
                            print(urls[b])
                            #wget.download(urls[b], FULL_PATH)  
                         

                        # let calculate the land surface temperature
                        try:
                            userUsed = current_user
                            TEMP_ID = str(userUsed.get_id())

                            folderName = sId["date"]
                            isCalculated = True

                            isCalculated = __applyLST__(SAVE_FOLDER_PATH,TEMP_ID,folderName)

                            if isCalculated == False:
                                logoutFromApi()
                                return render_template("heat.html",user = current_user,ErrorMsg = "Erreur il manque des fichier.tif!")

                        except:
                            logoutFromApi()
                            return render_template("heat.html",user = current_user,ErrorMsg = "Erreur lors calculer LST !essayer plus tard!")

                        
                    except:
                        logoutFromApi()
                        return render_template("heat.html",user = current_user,ErrorMsg = "Erreur lors le téléchargement les Scenes du profile!essayer plus tard!")
                    
                    
        
                    
            
            
            
            
            
            
            
            except:
                logoutFromApi()
                return render_template("heat.html",user = current_user,ErrorMsg = "Aucune Lien de téléchargement a été trouvé!")  
        
        ############# end of simple form #####################
        # 
        # 
        # #####################################################                  
        else :
            logoutFromApi()
            return render_template("heat.html",user = current_user,ErrorMsg = "Erreur Clé API,essayer plus tard!")                
    return render_template("heat.html",user = current_user,ErrorMsg="",aErrorMsg="")


    
################## handling advanced form sumbition

@view.route("/advancedForm",methods=['GET','POST'])
def advancedForme():

    if request.method == 'POST':
        # get user form
        advancedLocationName = request.form.get("Alocation")
        advancedStudyDate = request.form.get("dateFrom")
        advancedStudyProfileFrom = request.form.get("advancedStudyDateFrom")
        advancedStudyProfileTo = request.form.get("advancedStudyDateTo")

        if str(advancedLocationName) != "" and str(advancedStudyDate) != "" and str(advancedStudyProfileFrom) != "" and str(advancedStudyProfileTo) != "":
            
            # check if file names match the patter ie bandNum.tif => 4.tif
            user = current_user
            TEMP_ID = str(user.get_id())
            BANDS_PATH = os.path.join(UPLOAD_FOLDER, TEMP_ID)
            
            for file in os.listdir(BANDS_PATH):
                # check if current path is a file
                if os.path.isfile(os.path.join(BANDS_PATH, file)):
                    fileNameWitoutExt = str(file)[:-4]

                    isNumber = re.findall("[0-1][0-9]", fileNameWitoutExt)
                    
                    if isNumber == False:
                        return render_template("heat.html",user = current_user,ErrorMsg="",aErrorMsg="Les fichier exporter ont mauvaise notation")

            # at this point we got all required bands let calculate LST

            # #if all required bands are selected 4 5 10 11 continue

            __applyLST__(BANDS_PATH,TEMP_ID,"")

            #============end of lst calculation############            
            ###############################################
            #=======this section reserved for profile=====#
            
            profileStartDate = advancedStudyProfileFrom + "-01"
            profileEndDate = advancedStudyProfileTo+ "-30"
            print(profileStartDate)
            print(profileEndDate)
        
            lon = 0
            lat = 0

            #check if there is scenes with given infos
            # first we need to get API key will be valid for 1 hours and store it

            try:
                logoutFromApi()
                apiLogin,API_KEY = createSeason()
                print(API_KEY)
            except:
                return render_template("heat.html",user = current_user,ErrorMsg="",aErrorMsg= "Erreur Clé API,essayer plus tard!")
            if API_KEY is not None:
                # proceded with finding the desired location
                # first we need to get the long and lat of the location
                #    
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
                    return render_template("heat.html",user = current_user,ErrorMsg="",aErrorMsg= "Erreur lors la récuperation du position géographique!")
                

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
                        return render_template("heat.html",user = current_user,ErrorMsg="",aErrorMsg= "Aucune scenes a été trouve pour le profile et avec niveau 1!")
                                    
                    print(levelOneSceneIdList)
                    
                except:
                    logoutFromApi()
                    return render_template("heat.html",user = current_user,ErrorMsg="",aErrorMsg= "Aucune scenes a éte trouvé pour le profle d'étude!")
           
                try :
                    for sId in levelOneSceneIdList:
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
                        userUsed = current_user
                        TEMP_ID = str(userUsed.get_id())
                        PARENT_SAVE_FOLDER_PATH = os.path.join(UPLOAD_FOLDER, TEMP_ID)
                        SAVE_FOLDER_PATH = os.path.join(PARENT_SAVE_FOLDER_PATH,sId["date"])
                        try:
                            #print("making dir ")
                            if os.path.isdir(SAVE_FOLDER_PATH) == False:
                                os.mkdir(SAVE_FOLDER_PATH)
                        except:
                            logoutFromApi()
                            return render_template("heat.html",user = current_user,ErrorMsg="",aErrorMsg= "Erreu lors creation votre reportoire,essayer plus tards!")

                    # lets start the download and saving the .tif(s)
                        try:
                            for b in BANDS_LIST:
                                FULL_PATH = str(SAVE_FOLDER_PATH) + "/" + str(b) + ".tif"
                                print(urls[b])
                                #wget.download(urls[b], FULL_PATH)  
                            print("================end=================")                          
                        
                            # let calculate the land surface temperature
                            try:
                                userUsed = current_user
                                TEMP_ID = str(userUsed.get_id())

                                folderName = sId["date"]
                                isCalculated = True

                                isCalculated = __applyLST__(SAVE_FOLDER_PATH,TEMP_ID,folderName)

                                if isCalculated == False:
                                    logoutFromApi()
                                    return render_template("heat.html",user = current_user,aErrorMsg = "Erreur il manque des fichier.tif!")

                            except:
                                logoutFromApi()
                                return render_template("heat.html",user = current_user,aErrorMsg = "Erreur lors calculer LST !essayer plus tard!")               
                        except:
                            logoutFromApi()
                            return render_template("heat.html",user = current_user,ErrorMsg="",aErrorMsg= "Erreur lors le téléchargement les Scenes du profile!essayer plus tard!")
                except:
                    logoutFromApi()
                    return render_template("heat.html",user = current_user,ErrorMsg="",aErrorMsg= "Aucune Lien de téléchargement a été trouvé!")  
        
        

        else :
            return render_template("heat.html",user = current_user,ErrorMsg="",aErrorMsg="Des champs sont vides")
        
    return render_template("heat.html",user = current_user,ErrorMsg="",aErrorMsg="")



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

    TOA_10,TOA_11 = calculatesTOA(BAND_10,BAND_11)
    BT_10,BT_11 = calculateBT(TOA_10,TOA_11)
    NDVI = calculateNDVI(BAND_4,BAND_5)
    PV = calculatePV(NDVI)
    E = calculateEM(PV)
    LST_signleChannel_B10= calculateLSTSignalChannel(BT_10,E)
    LST_signleChannel_B11= calculateLSTSignalChannel(BT_11,E)

    return LST_signleChannel_B10,LST_signleChannel_B11


def __applyLST__(BANDS_PATH,serveFolderId,serverFolderDate):

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

            changeProjection(lstPath=SAVE_PATH_B10,outputPath=OUTPUT_PATH_B10)
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

    # static plot
    # timeStamp plot

    data = [
        ("01-01-2020",1965),
        ("02-01-2020",655),
        ("03-01-2020",1973),
        ("04-01-2020",1929),
        ("05-01-2020",2000),
        ("06-01-2020",1991),
        ("07-01-2020",298),
    ]

    labels = [row[0] for row in data]
    values = [row[1] for row in data]
    #print(labels)


    return render_template("dashboard.html",user = current_user,labels=[],band10Data=[],band11Data=[])

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

