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
# from eve.methods.patch import patch_internal
# from flask import abort
# from bson.objectid import ObjectId

# import numpy as np
# import math

from os.path import join, dirname
from dotenv import load_dotenv
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

from eve import Eve
app = Eve()

###########################################
# use default account for get trimble token
trimble_url=os.environ.get('TRIMBLE_API_URL')
trimble_email=os.environ.get('TRIMBLE_EMAIL')
trimble_key=os.environ.get('TRIMBLE_KEY')
def get_trimble_token():
    token=get_internal('token')[0]['_items'][0]["TrimbleToken"]
    headers={"Content-Type":"application/json","Authorization":"Bearer "+token}
    r = requests.get(trimble_url+'regions',headers=headers)
    if 'errorcode' not in r.json()['status']:
        return token
    # if token expired get a new one
    para={'emailAddress':trimble_email, 'key':trimble_key}
    headers={"Content-Type":"application/json"}
    r = requests.post(trimble_url+'auth',data=json.dumps(para),headers=headers)
    token=r.json()['token']
    data={"TrimbleToken":token}
    post_internal('entity',data)
    return token

# app.on_fetched_source_log+=get_trimble_token

if __name__ == '__main__':
    # app.run()
    # particularly for cloud 9 use
    app.run(host=os.environ['IP'],port=int(os.environ['PORT']),debug=True)