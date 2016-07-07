# Author: Ling Ma
# https://il.linkedin.com/in/cvlingma

import trimesh
import numpy as np

class Geom:
    extruded_axis=list()
    def __init__(self,data=None):
        if data == None:
            self.mesh=None
        else:
            self.loadMesh(data)
        
    def loadMesh(self,data):
        f_array=data['Faces']
        v_array=data['Vertices']
        n_array=data['Normals']
        try:
            self.mesh=trimesh.Trimesh(vertices=v_array,faces=f_array,vertex_normals=n_array)
        except:
            self.mesh=None
            
    # get minimal volume OBB
    def getOBBFeature(self):
        if self.mesh is None:
            print("mesh is not loaded")
            return None
        box=self.mesh.bounding_box_oriented
        ext = box.extents.tolist()
        centroid = box.centroid.tolist()
        axis=np.transpose(np.array(box.box_transform)[0:3,0:3]).tolist()
        # update the ext in local
        ext = np.absolute(np.dot(axis,ext))
        data = [
            {
            'Name':'TransformMatrix',
            'Description':'Transform from global to local?',
            'Value':np.transpose(box.box_transform).tolist()
            },
            {
            'Name':'Extent',
            'Description':'Dimension in local axis?',
            'Value':{
                'X':ext[0],
                'Y':ext[1],
                'Z':ext[2],
                }
            },
            {
            'Name':'OBBCentroid',
            'Description':'Cooridnate in global?',
            'Value':{
                'X':centroid[0],
                'Y':centroid[1],
                'Z':centroid[2],
                }
            },
            {
            'Name':'OBBAxis',
            'Description':'axes in global?',
            'Value':{
                'X':axis[0],
                'Y':axis[1],
                'Z':axis[2],
                },
            },
        ]
        greatest_value=0
        axis='X'
        extent=data[1]['Value']
        obb_axis=data[3]['Value']
        for key in extent:
            if greatest_value<extent[key]:
                axis=key
                greatest_value=extent[key]
        self.extruded_axis=obb_axis[axis]
        data.append({
            'Name':'ExtrudedAxis',
            'Description':'the major axis with greatest dimension',
            'Value':self.extruded_axis,
            })
        data.append({
            'Name':'ExtrusionLength',
            'Description':'the greatest dimension',
            'Value':greatest_value,
            })
        return data
    
    # get other shape features
    def getMeshFeature(self):
        if self.mesh is None:
            print("mesh is not loaded")
            return None
        data=[
            {
            'Name':'Centroid',
            'Description':'this is not always the same as OBB\'s',
            'Value':{
                'X':self.mesh.centroid[0],
                'Y':self.mesh.centroid[1],
                'Z':self.mesh.centroid[2]
                }
            },
            {
            'Name':'CenterMass',
            'Description':'center of mass, useful?',
            'Value':{
                'X':self.mesh.center_mass[0],
                'Y':self.mesh.center_mass[1],
                'Z':self.mesh.center_mass[2]
                },
            },
            {
            'Name':'Min',
            'Description':'min point in global',
            'Value':{
                'X':self.mesh.bounds[0][0],
                'Y':self.mesh.bounds[0][1],
                'Z':self.mesh.bounds[0][2]
                },
            },
            {
            'Name':'Max',
            'Description':'max point in global',
            'Value':{
                'X':self.mesh.bounds[1][0],
                'Y':self.mesh.bounds[1][1],
                'Z':self.mesh.bounds[1][2]
                }
            },
            {
            'Name':'IsConvex',
            'Description':'convex?',
            'Value':self.mesh.is_convex,
            },
            {
            'Name':'IsWaterTight',
            'Description':'very few cases not watertight',
            'Value':self.mesh.is_watertight,
            },
            {
            'Name':'MomentInertia',
            'Description':'useful?',
            'Value':self.mesh.moment_inertia.tolist(),
            },
            {
            'Name':'Volume',
            'Description':'gross volume',
            'Value':self.mesh.volume,
            }
        ]
        return data
    