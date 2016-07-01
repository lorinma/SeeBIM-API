# Author: Ling Ma
# https://il.linkedin.com/in/cvlingma
import ifcopenshell
import ifcopenshell.geom as geom
from utils import Util
settings = geom.settings()
settings.set(settings.SEW_SHELLS, True)
settings.set(settings.USE_WORLD_COORDS, True)
# unweld to get vertex normals
settings.set(settings.WELD_VERTICES, False)
# change units to mm
settings.set(settings.CONVERT_BACK_UNITS, True)

from bson.objectid import ObjectId
import os
import numpy as np

class IFC:
    def __init__(self):
        self.util=Util()
        pass
    
    #TODO Heroku doesn't allow store file on server?
    def parse_file(self,file_path,file_id):
        file = ifcopenshell.open(file_path)
        line_ids=file.wrapped_data.entity_names()
        data=list()
        for line_id in line_ids:
            entity = file.wrapped_data.by_id(line_id)
            entity_data = {"EntityType": entity.is_a(),"_id":str(ObjectId()),"Line":entity.id(),"Attribute":list()}
            entity_data["FileID"]= file_id
            data.append(entity_data)
        # if you are going to fetch repeatedly from name, you better construct a dictionary with the names as keys so get operations are O(1)
        data_indexed = self.util.re_index(data)
        # return data_indexed
        inx=-1
        for line_id in line_ids:
            inx+=1
            entity = file.wrapped_data.by_id(line_id)
            links=list()
            for attribute_name in entity.get_attribute_names():
                Editable=False
                attribute_value=entity.get_argument(attribute_name)
                if isinstance(attribute_value, tuple):
                    item_value=list()
                    for v in attribute_value:
                        if 'id' in dir(v):
                            v_line_id=v.id()
                            if v_line_id==0:
                                item_value.append(v.get_argument(0))
                                Editable=True
                            else:
                                _id=data_indexed[v_line_id]["_id"]
                                item_value.append(_id)
                                links.append(_id)
                        else:
                            if v is None:
                                v=""
                            item_value.append(v)
                            Editable=True
                else:        
                    if 'id' in dir(attribute_value):
                        attribute_line_id=attribute_value.id()
                        if attribute_line_id==0:
                            item_value=attribute_value.get_argument(0)
                            Editable=True
                        else:
                            item_value=data_indexed[attribute_line_id]["_id"]
                            links.append(item_value)
                    else:
                        if attribute_value is None:
                            attribute_value=""
                        item_value=attribute_value
                        Editable=True
                item=dict()
                item["Name"]=attribute_name
                item["Value"]=item_value
                item["Editable"]=Editable
                data[inx]["Attribute"].append(item)
            data[inx]["Links"]=links
        return data
    
    def parse_geometry(self,file_path,file_id):
        file = ifcopenshell.open(file_path)
        elements = file.by_type('IfcProduct')
        data=list()
        for entity_element in elements:
            if entity_element.Representation is None:
                continue
            if entity_element.is_a("IfcGrid"):
                continue
            element=dict()
            settings.set(settings.USE_BREP_DATA, True)
            shape = ifcopenshell.geom.create_shape(settings, entity_element)
            geometry = shape.geometry
            brep = geometry.brep_data
            element["OCEBrep"]=brep
            settings.set(settings.USE_BREP_DATA, False)
            shape = ifcopenshell.geom.create_shape(settings, entity_element)
            geometry = shape.geometry
            v=geometry.verts
            # convert from mm to m
            v_array=np.divide(np.array(v).reshape(int(len(v)/3),3),1000.)
            f=geometry.faces
            f_array=np.array(f).reshape(int(len(f)/3),3)
            n=geometry.normals
            n_array=np.array(n).reshape(int(len(n)/3),3)
            element["Vertices"]=v_array.tolist()
            element["Faces"]=f_array.tolist()
            element["Normals"]=n_array.tolist()
            element["Unit"]="m"
            data.append({
                "Geometry":element,
                "FileID":file_id,
                "GlobalId":entity_element.GlobalId
            })
        return data