from flask import Blueprint, render_template,request,redirect,url_for,make_response,flash,jsonify
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

UPLOAD_FOLDER = 'website\\temp\\'
ALLOWED_EXTENSIONS = {'tif'}

view = Blueprint("view",__name__)


def page_not_found(e):
  return render_template('error.html'), 404


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# url redirect
@view.route("/")
def goHome():
    return render_template("index.html",user = current_user)
@view.route("/heat")
@login_required
def goHeat():
    return render_template("heat.html",user = current_user)


@view.route("/simpleForm",methods=['GET','POST'])
@login_required
def simpleForme():
    if request.method == 'POST':

        # check if the submit comes from simple or advanced option

   
            # api approche
            #print("simple approche")
            # first we need to get the location name,desired date and study profile
        simpleLocationName = request.form.get("slocation")
        simpleStudyDate = request.form.get("simpleStudyDate")
        simpleStudyProfile = request.form.get("simpleProfileOption")
        print("simple")
        import time
        time.sleep(10)

            #check if there is scenes with given infos

            # first we need to get API key will be valid for 1 hours and store it

        # apiLogin,API_KEY = createSeason()
        # if API_KEY is not None:
        #         # proceded with finding the desired location
        #         # first we need to get the long and lat of the location
        #     address = simpleLocationName
        #     url = 'https://nominatim.openstreetmap.org/search/' + urllib.parse.quote(address) +'?format=json'
        #     response = requests.get(url).json()

        #     lat = float(response[0]["lat"])
        #     lon = float(response[0]["lon"])

        #         # second create timestamp ie 2023-03 => 2023-03-01 -> 2023-03-30

        #     startDate = simpleStudyDate + "-01"
        #     endDate = simpleStudyDate + "-30"
                
        #         # search for the scene with LC08_L1 from 'display_id': 'LC09_L1TP_198035_20230326_20230326_02_T1'
        #     flash("Searching scenes")
        #     scenes = searchForScene(apiLogin=apiLogin,
        #                                 lat=lat,
        #                                 long=lon,
        #                                 startData=startDate,
        #                                 endDate=endDate)
                
        #     if scenes is not None:
        #         sceneId,productId = getScenesWithL1(scenes=scenes)
        #             # get the bands download ids
        #         if sceneId is not None:
        #             downloadOptions = getDownloadOption(entity_id=sceneId[0],API_KEY=API_KEY)
        #             bandsDownloadId = getIDsForDownloadUrlForBand(bandsList=BANDS_LIST,downloadOptions=downloadOptions)

        #                 # bandsDownloadId is dict ie {bandNum:{entityId,productId}}

        #             downloadUrls = {}
        #             for band in BANDS_LIST:
        #                 b = {"entityId":bandsDownloadId[band]["entityId"],
        #                          "productId":bandsDownloadId[band]["productId"]}
                            
        #                 downloadUrls[band] = getDownloadUrl(bandsIds=b,API_KEY=API_KEY)
        #                 #print(downloadUrls)
        #                 print(downloadUrls[10])

        #                 #create dir with using id of this user

        #                 user = current_user
        #                 TEMP_ID = str(user.get_id())
        #                 #print(TEMP_ID)
        #                 SAVE_FOLDER_PATH = os.path.join(UPLOAD_FOLDER, TEMP_ID)
        #                 os.mkdir(SAVE_FOLDER_PATH)

        #                 FULL_PATH = str(SAVE_FOLDER_PATH) + "/10.tif"
        #                 # now we need to download the .tif and store it in a temp folder

        #                 #req = requests.get(downloadUrls[10], allow_redirects=True)
        #                 #wget.download(downloadUrls[10], FULL_PATH)
    return render_template("heat.html",user = current_user)


    


@view.route("/advancedForm",methods=['GET','POST'])
@login_required
def advancedForme():

    if request.method == 'POST':
        # get user form
        advancedLocationName = request.form.get("Alocation")
        advancedStudyDate = request.form.get("dateFrom")
        advancedStudyProfile = request.form.get("advancedProfileOption")
        
        #check if all bands are stored before continue
        #get all bands from temp/userIdfolder folder

        user = current_user
        TEMP_ID = str(user.get_id())
        BANDS_BATH = os.path.join(UPLOAD_FOLDER, TEMP_ID)

        bands,isFull = getBands(BANDS_BATH,BANDS_LIST)

        #if all required bands are selected 4 5 10 11 continue

        if isFull == True :

            # Calculate LST 
            LST_B10,LST_B11 = calcLST_SC(bands)

            # save the result











        #this section reserved for profile
        #download and calculate lst
        #
        #
        #


    return render_template("heat.html",user = current_user)



############# end calculate function ####################


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