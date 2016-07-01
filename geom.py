# Author: Ling Ma
# https://il.linkedin.com/in/cvlingma

import trimesh
import numpy as np

class Geom:
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
    def getOBB(self):
        if self.mesh is None:
            print("mesh is not loaded")
            return None
        box=self.mesh.bounding_box_oriented
        ext = box.extents.tolist()
        centroid = box.centroid.tolist()
        axis=np.transpose(np.array(box.box_transform)[0:3,0:3]).tolist()
        data = [
            {
            'Name':'TransformMatrix',
            'Value':np.transpose(box.box_transform).tolist()
            },
            {
            'Name':'Extent',
            'Value':{
                'X':ext[0],
                'Y':ext[1],
                'Z':ext[2],
                }
            },
            {
            'Name':'OBBCentroid',
            'Value':{
                'X':centroid[0],
                'Y':centroid[1],
                'Z':centroid[2],
                }
            },
            {
            'Name':'OBBAxis',
            'Value':{
                'X':axis[0],
                'Y':axis[1],
                'Z':axis[2],
                },
            },
        ]
        return data
    
    # get other shape features
    def getMeshFeature(self):
        if self.mesh is None:
            print("mesh is not loaded")
            return None
        centroid=self.mesh.centroid.tolist(),
        center_mass=self.mesh.center_mass.tolist(),
        min=self.mesh.bounds[0].tolist(),
        max=self.mesh.bounds[1].tolist(),
        data=[
            {
            'Name':'Centroid',
            'Value':{
                'X':self.mesh.centroid[0],
                'Y':self.mesh.centroid[1],
                'Z':self.mesh.centroid[2]
                }
            },
            {
            'Name':'CenterMass',
            'Value':{
                'X':self.mesh.center_mass[0],
                'Y':self.mesh.center_mass[1],
                'Z':self.mesh.center_mass[2]
                },
            },
            {
            'Name':'Min',
            'Value':{
                'X':self.mesh.bounds[0][0],
                'Y':self.mesh.bounds[0][1],
                'Z':self.mesh.bounds[0][2]
                },
            },
            {
            'Name':'Max',
            'Value':{
                'X':self.mesh.bounds[1][0],
                'Y':self.mesh.bounds[1][1],
                'Z':self.mesh.bounds[1][2]
                }
            },
            {
            'Name':'IsConvex',
            'Value':self.mesh.is_convex,
            },
            {
            'Name':'IsWaterTight',
            'Value':self.mesh.is_watertight,
            },
            {
            'Name':'MomentInertia',
            'Value':self.mesh.moment_inertia.tolist(),
            },
            {
            'Name':'Volume',
            'Value':self.mesh.volume,
            }
        ]
        return data
    