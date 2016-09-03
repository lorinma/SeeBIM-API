# Author: Dr. Ling Ma
# https://il.linkedin.com/in/cvlingma

import ifcopenshell
import ifcopenshell.geom as geom
import numpy as np

class IFC:
    def __init__(self,file_path):
        self.file = ifcopenshell.open(file_path)
        self.settings = geom.settings()
        # self.settings.set(self.settings.APPLY_DEFAULT_MATERIALS, True)
        # Specifies whether to convert back geometrical output back to the unit of measure in which it is defined in the IFC file. Default is to use meters.
        # self.settings.set(self.settings.CONVERT_BACK_UNITS, False)
        # self.settings.set(self.settings.DISABLE_OPENING_SUBTRACTIONS, False)
        # self.settings.set(self.settings.DISABLE_TRIANGULATION, False)
        # self.settings.set(self.settings.EXCLUDE_SOLIDS_AND_SURFACES, False)
        # self.settings.set(self.settings.FASTER_BOOLEANS, True)
        # self.settings.set(self.settings.INCLUDE_CURVES, True)
        # self.settings.set(self.settings.SEW_SHELLS, True)
        # # get triangular mesh instead of OCE_BREP
        # self.settings.set(self.settings.USE_BREP_DATA, False)
        self.settings.set(self.settings.USE_WORLD_COORDS, True)
        # # unweld to get vertex normals
        # self.settings.set(self.settings.WELD_VERTICES, False)
    
    def parse_geometry(self):
        elements = self.file.by_type('IfcProduct')
        data=list()
        entities=list()
        for entity_element in elements:
            if entity_element.Representation is None:
                continue
            try:
                shape = ifcopenshell.geom.create_shape(self.settings, entity_element)
            except:
                continue
            geometry = shape.geometry
            v=geometry.verts
            # default is meter, change to mm
            v_array=np.array(v).reshape(int(len(v)/3),3)*1000
            f=geometry.faces
            f_array=np.array(f).reshape(int(len(f)/3),3)
            n=geometry.normals
            n_array=np.array(n).reshape(int(len(n)/3),3)
            element=dict()
            element["Vertices"]=v_array.tolist()
            element["Faces"]=f_array.tolist()
            element["Normals"]=n_array.tolist()
            element["Unit"]="mm"
            data.append({
                "Geometry":element,
                # "FileID":file_id,
                "GlobalId":entity_element.GlobalId
            })
            entities.append({
                "IFCType":entity_element.is_a(),
                "GlobalId":entity_element.GlobalId
            })
        return (entities,data)