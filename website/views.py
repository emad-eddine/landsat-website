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
@view.route("/board")
@login_required
def goBoard():
    return render_template("dashboard.html",user = current_user)



################## handling form sumbition
@view.route("/simpleForm",methods=['GET','POST'])
def simpleForme():
    if request.method == 'POST':
        # api approche
        #print("simple approche")
        # first we need to get the location name,desired date and study profile
        simpleLocationName = request.form.get("slocation")
        simpleStudyDate = request.form.get("simpleStudyDate")
        simpleStudyProfile = request.form.get("simpleProfileOption")


        #check if there is scenes with given infos
        # first we need to get API key will be valid for 1 hours and store it

        try:
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
            downloadUrlLists = searchScenesLevel1(apiLogin=apiLogin,
                                                  lat=lat,
                                                  lon=lon,
                                                  startDate=startDate,
                                                  endDate=endDate,
                                                  API_KEY=API_KEY,
                                                  allScenes=False)
          
            try :
                #check if there is dir with user id if not lets  create onn

                user = current_user
                TEMP_ID = str(user.get_id())
                SAVE_FOLDER_PATH = os.path.join(UPLOAD_FOLDER, TEMP_ID)
                
                try:
                    if os.path.isdir(SAVE_FOLDER_PATH) == False:
                        os.mkdir(SAVE_FOLDER_PATH)
                except:
                    logoutFromApi()
                    return render_template("heat.html",user = current_user,ErrorMsg = "Erreu lors creation votre reportoire,essayer plus tards!")

                # lets start the download and saving the .tif(s)
                try:
                    for url in downloadUrlLists:
                        for band in BANDS_LIST:
                            FULL_PATH = str(SAVE_FOLDER_PATH) + "/" + str(band) + ".tif"
                            wget.download(url[band], FULL_PATH)
                except:
                    logoutFromApi()
                    return render_template("heat.html",user = current_user,ErrorMsg = "Erreur lors téléchargement des Scenes!essayer plus tard!")
            except:
                logoutFromApi()
                return render_template("heat.html",user = current_user,ErrorMsg = "Aucune Scene a été trouvé!")

            # so far we should have all the bands we need to calculate LST

            user = current_user
            TEMP_ID = str(user.get_id())
            BANDS_PATH = os.path.join(UPLOAD_FOLDER, TEMP_ID)
            PARENT_RESULT_PATH = os.path.join(BANDS_PATH, "results")
            try:
                if os.path.isdir(PARENT_RESULT_PATH) == False:
                    os.mkdir(PARENT_RESULT_PATH)
            except:
                logoutFromApi()
                return render_template("heat.html",user = current_user,ErrorMsg = "Erreu lors creation reporatoire des resultat,essayer plus tards!")
            
            RESULT_PATH = os.path.join(PARENT_RESULT_PATH, "result.tif")

            bands,isFull = getBands(BANDS_PATH,BANDS_LIST)

            # #if all required bands are selected 4 5 10 11 continue

            if isFull == True :

            # Calculate LST 
                LST_B10,LST_B11 = calcLST_SC(bands)

            # save the result
            
            #saveLSTInTif(imagery=bands[10],lst=LST_B10,path=RESULT_PATH)

            else :
                logoutFromApi()
                return render_template("heat.html",user = current_user,ErrorMsg = "Erreu lors calculer LST,essayer plus tards!")




            ###################################
            # after that lets handel the profile
            # get number of months
            if str(simpleStudyProfile) == "" or simpleStudyProfile is None:
                   logoutFromApi()
                   return render_template("heat.html",user = current_user,ErrorMsg = "Aucune profile a été choisi!")  
            else:
                #repeate the pre traitment
                numberOfIteration = 0
                if str(simpleStudyProfile) == "3m":
                    numberOfIteration = 3
                elif str(simpleStudyProfile) == "6m":
                    numberOfIteration = 6
                elif str(numberOfIteration) == "12m":
                    numberOfIteration = 12

                for i in range(1,numberOfIteration+1):
                    # ie 2023-03 we need the year
                    if i < 10:
                        profileStarDate = str(simpleStudyDate)[0:4] +"-0" + i + "-01"
                        profileEndDate = str(simpleStudyDate)[0:4] +"-0" + i + "-30"
                    elif i >=10:
                        profileStarDate = str(simpleStudyDate)[0:4] +"-0" + i + "-01"
                        profileEndDate = str(simpleStudyDate)[0:4] +"-0" + i + "-30"

                    #start the search
                    downloadUrlLists = searchScenesLevel1(apiLogin=apiLogin,
                                                  lat=lat,
                                                  lon=lon,
                                                  startDate=profileStarDate,
                                                  endDate=profileEndDate,
                                                  API_KEY=API_KEY,
                                                  allScenes=False)
                    
                    if downloadUrlLists is None:
                        print("error aucune donnee")
                    else:
                        print(downloadUrlLists[0])
          
                    try :
                        #check if there is dir with user id if not lets  create one

                        user = current_user
                        TEMP_ID = str(user.get_id())
                        PARENT_FOLDER_PATH = os.path.join(UPLOAD_FOLDER, TEMP_ID)
                        SAVE_FOLDER_PATH = os.path.join(PARENT_FOLDER_PATH, i)
                
                        try:
                            if os.path.isdir(SAVE_FOLDER_PATH) == False:
                                os.mkdir(SAVE_FOLDER_PATH)
                        except:
                            logoutFromApi()
                            return render_template("heat.html",user = current_user,ErrorMsg = "Erreu lors creation votre reportoire,essayer plus tards!")

                    # lets start the download and saving the .tif(s)
                        try:
                            for url in downloadUrlLists:
                                for band in BANDS_LIST:
                                    FULL_PATH = str(SAVE_FOLDER_PATH) + "/" + str(band) + ".tif"
                                    print(url[band])
                                    wget.download(url[band], FULL_PATH)
                        except:
                            logoutFromApi()
                            return render_template("heat.html",user = current_user,ErrorMsg = "Erreur lors téléchargement des Scenes!essayer plus tard!")

                    except:
                        logoutFromApi()
                        return render_template("heat.html",user = current_user,ErrorMsg = "Aucune Scene a été trouvé!")
        else :
            logoutFromApi()
            return render_template("heat.html",user = current_user,ErrorMsg = "Erreur Clé API,essayer plus tard!")                
    return render_template("heat.html",user = current_user)


    
################## handling advanced form sumbition

@view.route("/advancedForm",methods=['GET','POST'])
def advancedForme():

    if request.method == 'POST':
        # get user form
        advancedLocationName = request.form.get("Alocation")
        advancedStudyDate = request.form.get("dateFrom")
        advancedStudyProfile = request.form.get("advancedProfileOption")

        if str(advancedLocationName) != "" and str(advancedStudyDate) != "" and str(advancedStudyProfile) != "":
            
            # check if file names match the patter ie bandNum.tif => 4.tif

            user = current_user
            TEMP_ID = str(user.get_id())
            BANDS_PATH = os.path.join(UPLOAD_FOLDER, TEMP_ID)
            
            # for file in os.listdir(BANDS_PATH):
            #     # check if current path is a file
            #     if os.path.isfile(os.path.join(BANDS_PATH, file)):
            #         fileNameWitoutExt = str(file)[:-4]

            #         isNumber = re.findall("[0-1][0-9]", fileNameWitoutExt)
                    
            #         if isNumber == False:
            #             return render_template("heat.html",user = current_user,ErrorMsg="",aErrorMsg="Les fichier exporter ont mauvaise notation")

            # at this point we got all required bands let calculate LST

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
                    SAVE_FOLDER_PATH = os.path.join(RESULT_BATH, TEMP_ID)
                
                    try:
                        if os.path.isdir(SAVE_FOLDER_PATH) == False:
                             os.mkdir(SAVE_FOLDER_PATH)
                    except:
                        return render_template("heat.html",user = current_user,ErrorMsg="",aErrorMsg="Erreur lors Créer la résultat! Essayer plus tards")
                    
                    OUTPUT_PATH_B10 = os.path.join(SAVE_FOLDER_PATH,"r_10.tif")
                    OUTPUT_PATH_B11 = os.path.join(SAVE_FOLDER_PATH,"r_11.tif")

                    changeProjection(lstPath=SAVE_PATH_B10,outputPath=OUTPUT_PATH_B10)
                    changeProjection(lstPath=SAVE_PATH_B11,outputPath=OUTPUT_PATH_B11)


                    ### delete the temp folder

                except:
                    return render_template("heat.html",user = current_user,ErrorMsg="",aErrorMsg="Erreur lors calculer LST! Essayer plus tards")


            else:
                return render_template("heat.html",user = current_user,ErrorMsg="",aErrorMsg="Il manque des fichier .Tif") 
        else :
            return render_template("heat.html",user = current_user,ErrorMsg="",aErrorMsg="Des champs sont vides")

       
        #this section reserved for profile
        #download and calculate lst
        #
        #
        #


    return render_template("heat.html",user = current_user)



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

######## this function will handel the following ###

# searching for scenes
# return list that contain download link

# inputs scenes Params

def searchScenesLevel1(apiLogin,lat,lon,startDate,endDate,API_KEY,allScenes):

    scenes = searchForScene(apiLogin=apiLogin,
                                        lat=lat,
                                        long=lon,
                                        startData=startDate,
                                        endDate=endDate)
    try :
        #get level 1 scenes
        sceneId,productId = getScenesWithL1(scenes=scenes)
                
        #the search may give us many scenes with l1 we can use just one of them
        # get the bands download ids
        downloadOptions = []
        downloadUrlLists = []
        if allScenes == False :
            downloadOptions.append(getDownloadOption(entity_id=sceneId[0],API_KEY=API_KEY))
        # get all the result
        elif allScenes == True:
            for id in sceneId:
                downloadOptions.append(getDownloadOption(entity_id=sceneId[id],API_KEY=API_KEY))
        for op in downloadOptions:
            bandsDownloadId = getIDsForDownloadUrlForBand(bandsList=BANDS_LIST,downloadOptions=op)

            # bandsDownloadId is dict ie {bandNum:{entityId,productId}}
            downloadUrls = {}

            for band in BANDS_LIST:
                b = {"entityId":bandsDownloadId[band]["entityId"],
                        "productId":bandsDownloadId[band]["productId"]}
                            
                downloadUrls[band] = getDownloadUrl(bandsIds=b,API_KEY=API_KEY)
            downloadUrlLists.append(downloadUrls)
        return downloadUrlLists
    except:
        return None

####### end searching function #########################


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




