from flask import Blueprint, render_template,request,redirect,url_for,make_response,flash
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

@view.route("/heat",methods=['GET','POST'])
@login_required
def goHeat():

    if request.method == 'POST':

        # check if the submit comes from simple or advanced option

        if(request.form.get("form_name") == "simple"):
            # api approche
            #print("simple approche")
            # first we need to get the location name,desired date and study profile
            simpleLocationName = request.form.get("slocation")
            simpleStudyDate = request.form.get("simpleStudyDate")
            simpleStudyProfile = request.form.get("simpleProfileOption")

            #check if there is scenes with given infos

            # first we need to get API key will be valid for 1 hours and store it

            apiLogin,API_KEY = createSeason()
            if API_KEY is not None:
                # proceded with finding the desired location
                # first we need to get the long and lat of the location
                address = simpleLocationName
                url = 'https://nominatim.openstreetmap.org/search/' + urllib.parse.quote(address) +'?format=json'
                response = requests.get(url).json()

                lat = float(response[0]["lat"])
                lon = float(response[0]["lon"])

                # second create timestamp ie 2023-03 => 2023-03-01 -> 2023-03-30

                startDate = simpleStudyDate + "-01"
                endDate = simpleStudyDate + "-30"
                
                # search for the scene with LC08_L1 from 'display_id': 'LC09_L1TP_198035_20230326_20230326_02_T1'
                flash("Searching scenes")
                scenes = searchForScene(apiLogin=apiLogin,
                                        lat=lat,
                                        long=lon,
                                        startData=startDate,
                                        endDate=endDate)
                
                if scenes is not None:
                    sceneId,productId = getScenesWithL1(scenes=scenes)
                    # get the bands download ids
                    if sceneId is not None:
                        downloadOptions = getDownloadOption(entity_id=sceneId[0],API_KEY=API_KEY)
                        bandsDownloadId = getIDsForDownloadUrlForBand(bandsList=BANDS_LIST,downloadOptions=downloadOptions)

                        # bandsDownloadId is dict ie {bandNum:{entityId,productId}}

                        downloadUrls = []
                        for band in BANDS_LIST:
                            b = {"entityId":bandsDownloadId[band]["entityId"],
                                 "productId":bandsDownloadId[band]["productId"]}
                            
                            downloadUrls.append({band:getDownloadUrl(bandsIds=b,API_KEY=API_KEY)})

                        #print(downloadUrls)


        # handel huge landsat-8 files upload
        elif (request.form.get("form_name")== "advanced"):
            # files upload approch
            #print("advanced approche")


            # get user form
            advancedLocationName = request.form.get("Alocation")
            advancedStudyDate = request.form.get("dateFrom")
            advancedStudyProfile = request.form.get("advancedProfileOption")
            # get the files

            # Get the list of files from webpage
            files = request.files.getlist("landFiles")

            #create dir with using id of this user

            user = current_user
            TEMP_ID = str(user.get_id())
            #print(TEMP_ID)


            SAVE_FOLDER_PATH = os.path.join(UPLOAD_FOLDER, TEMP_ID)


            os.mkdir(SAVE_FOLDER_PATH)
            
  
            # Iterate for each file in the files List, and Save them
            for file in files:
                file.save(os.path.join(SAVE_FOLDER_PATH, file.filename))

            # calculate the LST and save the shapeFile



       

    return render_template("heat.html",user = current_user)


############# end calculate function ####################