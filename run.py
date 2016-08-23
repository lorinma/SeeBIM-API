# Author: Dr. Ling Ma
# https://il.linkedin.com/in/cvlingma

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

from eve import Eve
app = Eve()

###########################################
# use default account for get trimble token and project folder
trimble_url=os.environ.get('TRIMBLE_API_URL')
trimble_email=os.environ.get('TRIMBLE_EMAIL')
trimble_key=os.environ.get('TRIMBLE_KEY')
trimble_folder_id=os.environ.get('TRIMBLE_FolderID')

def get_trimble_token():
    data=get_internal('token')[0]['_items']
    # print(data)
    if len(data)>0:
        token=data[0]["TrimbleToken"]
        headers={"Content-Type":"application/json","Authorization":"Bearer "+token}
        r = requests.get(trimble_url+'regions',headers=headers)
        if 'errorcode' not in r.json():
            return token    
    # if token expired get a new one
    para={'emailAddress':trimble_email, 'key':trimble_key}
    headers={"Content-Type":"application/json"}
    r = requests.post(trimble_url+'auth',data=json.dumps(para),headers=headers)
    token=r.json()['token']
    data={"TrimbleToken":token}
    post_internal('log',data)
    return token

def add_file(items):
    for item in items:
        # download file
        file=IO()
        file_path=file.save_file(item['Url'])
        
        # upload to trimble
        token=get_trimble_token()
        headers={"Authorization":"Bearer "+token}
        files = {'file': open(file_path, 'rb')}
        r = requests.post(trimble_url+'files?parentId='+trimble_folder_id,files=files,headers=headers)
        trimble_data=r.json()[0]
        file_id=trimble_data['versionId']
        item['TrimbleVersionID']=file_id
        item['TrimbleProjectID']=trimble_data['projectId']
        
        # extract features from ifc file
        ifc=IFC(file_path)
        data=ifc.parse_geometry()
        file.remove_file(file_path)
        bim=Model(data=data,model_id=file_id)
        features=bim.get_features()
        print(features[1])
        # check if model is parsed in trimble
        r = requests.get(trimble_url+'files/'+file_id,headers=headers)
        thumbnailUrl=r.json()['thumbnailUrl'][0]
        item['ThumbnailUrl']=process_thumbnail(thumbnailUrl) if "http" in thumbnailUrl else ""
        post_internal('feature',features)

def process_thumbnail(url):
    if not url=="":
        import uuid
        token=get_trimble_token()
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
    # token=get_trimble_token()
    for item in data['_items']:
        if item['ThumbnailUrl']=="":
            token=get_trimble_token()
            file_id=item['TrimbleVersionID']
            headers={"Authorization":"Bearer "+token}
            r = requests.get(trimble_url+'files/'+file_id,headers=headers)
            thumbnailUrl=r.json()['thumbnailUrl'][0]
            thumbnailUrl=process_thumbnail(thumbnailUrl) if "http" in thumbnailUrl else ""
            if thumbnailUrl=="":
                continue
            item['ThumbnailUrl']=thumbnailUrl
            payload={
                "ThumbnailUrl":thumbnailUrl
            }
            patch_internal('file',payload,**{'_id': item['_id']})
            
app.on_fetched_resource_file+=get_files

def get_viewer_data(item):
    item['token']=get_trimble_token()
    
app.on_fetched_item_viewer+=get_viewer_data

def remove_files(item):
    payload={
        "UserID":'removed-by-' + item['UserID']
    }
    patch_internal('file',payload,**{'_id': item['_id']})

app.on_fetched_item_fileRemove+=remove_files
if __name__ == '__main__':
    # app.run()
    # particularly for cloud 9 use
    app.run(host=os.environ['IP'],port=int(os.environ['PORT']),debug=True)