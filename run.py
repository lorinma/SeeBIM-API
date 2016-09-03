# Author: Dr. Ling Ma
# https://il.linkedin.com/in/cvlingma

# use eve + mongo instead of hosing on Google firebase, because the latter only supports pure nodejs app
# however the api needs ifcopenshell python anyway, in addition, eve is a advanced REST api framework

import os
# from eve.io.mongo import Validator
import requests
import json
import schema
from eve.methods.get import get_internal,getitem_internal
# from eve.methods.delete import deleteitem_internal
from eve.methods.post import post_internal
from eve.methods.patch import patch_internal
# from flask import abort
# from bson.objectid import ObjectId

# import numpy as np
# import math
from os.path import join, dirname
from dotenv import load_dotenv
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

from util_io import IO
from util_ifc import IFC
from util_model import Model

import jwt
import datetime

from eve import Eve
app = Eve()

###########################################
# use default account for get trimble token and project folder
trimble_url=os.environ.get('TRIMBLE_API_URL')
trimble_email=os.environ.get('TRIMBLE_EMAIL')
trimble_key=os.environ.get('TRIMBLE_KEY')
trimble_folder_id=os.environ.get('TRIMBLE_FolderID')

def get_token(data):
    items=data['_items']
    if len(items)>0:
        token = items[0]['TrimbleToken']
        exp = jwt.decode(token,verify=False)['exp']
        now=datetime.datetime.now().timestamp()
        if now+120<exp:
            data['_items']={
                'token':token
            }
            return
    para={'emailAddress':trimble_email, 'key':trimble_key}
    headers={"Content-Type":"application/json"}
    r = requests.post(trimble_url+'auth',data=json.dumps(para),headers=headers)
    token=r.json()['token']
    payload={"TrimbleToken":token}
    post_internal('log',payload)
    data['_items']={
        'token':token
    }
app.on_fetched_resource_lastToken+=get_token

###########################################
# add a file and process model thumnail, which is uploaded to http://uploads.im
def add_file(items):
    for item in items:
        # download file
        file=IO()
        file_path=file.save_file(item['Url'])
        # upload to trimble
        token=get_internal('lastToken')[0]['_items']['token']
        # token=get_trimble_token()
        headers={"Authorization":"Bearer "+token}
        files = {'file': open(file_path, 'rb')}
        r = requests.post(trimble_url+'files?parentId='+trimble_folder_id,files=files,headers=headers)
        trimble_data=r.json()[0]
        TrimbleVersionID=trimble_data['versionId']
        item['TrimbleVersionID']=TrimbleVersionID
        item['TrimbleProjectID']=trimble_data['projectId']
        # extract features from ifc file
        ifc=IFC(file_path)
        entities, data=ifc.parse_geometry()
        file.remove_file(file_path)
        bim=Model(data=data,model_id=TrimbleVersionID)
        features=bim.get_features()
        # check if model is parsed in trimble
        r = requests.get(trimble_url+'files/'+TrimbleVersionID,headers=headers)
        thumbnailUrl=r.json()['thumbnailUrl'][0]
        item['ThumbnailUrl']=process_thumbnail(thumbnailUrl) if "http" in thumbnailUrl else ""
        item['Entities']=entities
        post_internal('feature',features)
def process_thumbnail(url):
    if not url=="":
        import uuid
        token=get_internal('lastToken')[0]['_items']['token']
        # token=get_trimble_token()
        headers={"Authorization":"Bearer "+token}
        trimble_thumb = requests.get(url,headers=headers)
        filename=str(uuid.uuid4())+".jpg"
        with open(filename, 'wb') as f:
            f.write(trimble_thumb.content)
        file = {"upload":open(filename, 'rb')}
        # http://uploads.im/apidocs is a service for free hosting and sharing img
        im_thumb = requests.post('http://uploads.im/api',files=file)
        data=im_thumb.json()
        os.remove(filename)
        return data['data']['thumb_url']
    return ""
app.on_insert_file+=add_file
def get_files(data):
    for item in data['_items']:
        if item['ThumbnailUrl']=="":
            token=get_internal('lastToken')[0]['_items']['token']
            TrimbleVersionID=item['TrimbleVersionID']
            headers={"Authorization":"Bearer "+token}
            r = requests.get(trimble_url+'files/'+TrimbleVersionID,headers=headers)
            thumbnailUrl=r.json()['thumbnailUrl'][0]
            thumbnailUrl=process_thumbnail(thumbnailUrl) if "http" in thumbnailUrl else ""
            if thumbnailUrl=="":
                continue
            item['ThumbnailUrl']=thumbnailUrl
            payload={
                "ThumbnailUrl":thumbnailUrl
            }
            patch_internal('file',payload,**{'_id': item['_id']})
app.on_fetched_resource_fileList+=get_files

###########################################
# 'remove a model' actually only changes the owner/user of the model, so that the model is kept in DB
def remove_files(item):
    payload={
        "UserID":'removed-by-' + item['UserID']
    }
    patch_internal('file',payload,**{'_id': item['_id']})
app.on_fetched_item_fileRemove+=remove_files

###########################################
# in addition to TrimbleVersionID and TrimbleProjectID, the viewer also requires a valid token
def get_viewer_data(item):
    item['token']=get_internal('lastToken')[0]['_items']['token']
app.on_fetched_item_viewer+=get_viewer_data

###########################################
# get all the features, the pairwise feature's value is reversed, this helps front end viewer to easily hide these objects 
def get_feature_view(data):
    items=data['_items']
    if len(items)==0:
        return
    TrimbleVersionID=items[0]['TrimbleVersionID']
    entities=getitem_internal('file',**{'TrimbleVersionID': TrimbleVersionID})[0]['Entities']
    all=list()
    for entity in entities:
        all.append(entity['GlobalId'])
    for item in items:
        hide=all[:]
        if item['FeatureType']=='Pairwise' and item['FeatureProvider']=='System':
            show=item['FeatureValue']
            show.append(item['GlobalId'])
            for show_obj in show:
                hide.remove(show_obj)
            item['FeatureValue']=hide
app.on_fetched_resource_featureVisual+=get_feature_view

if __name__ == '__main__':
    # app.run()
    # particularly for cloud 9 use
    app.run(host=os.environ['IP'],port=int(os.environ['PORT']),debug=True)