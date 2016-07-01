# Author: Ling Ma
# https://il.linkedin.com/in/cvlingma

import requests
from os.path import join, dirname
import os
from bson.objectid import ObjectId
import trimesh
import numpy as np

class Util:
    def __init__(self):
        self.static_path = join(dirname(__file__))
        pass
    
    def save_file(self,url):
        r = requests.get(url)
        self.filename=str(ObjectId())+".ifc"
        file_path=join(self.static_path,self.filename)
        with open(file_path, 'wb') as f:
            f.write(r.content)
        return file_path
    
    def is_objID(self,data):
        if ObjectId.is_valid(data) and str(ObjectId(data))==data:
            return True
        else:
            return False

    def remove_file(self,file_path):
        os.remove(file_path)
        
    def re_index(self,data):
        return dict((d["Line"], dict(d, index=i)) for (i, d) in enumerate(data))