# Author: Dr. Ling Ma
# https://il.linkedin.com/in/cvlingma

from os.path import join, dirname
import os
import json
import uuid


class IO:
    def __init__(self):
        self.static_path = join(dirname(__file__))
        pass
    
    def write_json(self,data,file_name='data.json'):
        with open(file_name, 'w') as outfile:
            json.dump(data, outfile)
    
    def load_json(self,file_name='data.json'):
        return json.loads(open(file_name).read())
        
    def save_file(self,url):
        import requests
        r = requests.get(url)
        filename=str(uuid.uuid4())+".ifc"
        file_path=join(self.static_path,filename)
        with open(file_path, 'wb') as f:
            f.write(r.content)
        return file_path

    def remove_file(self,file_path):
        os.remove(file_path)
        
    def re_index(self,data):
        return dict((d["Line"], dict(d, index=i)) for (i, d) in enumerate(data))