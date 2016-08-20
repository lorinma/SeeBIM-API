# Author: Dr. Ling Ma
# https://il.linkedin.com/in/cvlingma

import trimesh
import numpy as np
import math
from fcl import fcl
from fcl import collision_data as cd
class Geom:
    def __init__(self,data=None):
        if data == None:
            self.mesh=None
            self.bvh=None
        else:
            self.loadMesh(data)
            self.loadBVH(data)
    
    threshhold_degree=5
    
    def loadMesh(self,data):
        self.mesh=trimesh.Trimesh(vertices=data['Vertices'],faces=data['Faces'])
        # get minimal volume OBB
        self.obb=self.mesh.bounding_box_oriented
        # box_transform is transform the box to global
        self.axis=np.transpose(np.array(self.obb.box_transform)[0:3,0:3])
        # update the extents in global
        self.dimensions = np.absolute(np.dot(self.axis,self.obb.box_extents))
        # check if if there is a cross section which two dimensions are close (rotio<1.2), then the other axis is the extruded direction
        #TODO find a better way for identification of extruded direction
        for i in range(2):
            for j in range(3):
                if j<=i:
                    continue
                inx=[0,1,2]
                # axes=self.axis.tolist()
                # extents=self.obb.box_extents.tolist()
                if self.obb.box_extents[i]/self.obb.box_extents[j]<1.2 and self.obb.box_extents[j]/self.obb.box_extents[i]<1.2:
                    inx.remove(i)
                    inx.remove(j)
                    break
            if len(inx)==1:
                extrude_inx=inx[0]
                break
        # if there is no clear cross section, then use the longest axis
        if len(inx)!=1:
            extrude_inx=np.argsort(self.obb.box_extents)[2]
        self.extruded_axis=self.axis[extrude_inx]
        self.extruded_length=self.obb.box_extents[extrude_inx]
        
        self.box_center=self.obb.box_center
        self.min=self.mesh.bounds[0]
        self.max=self.mesh.bounds[1]
        self.volume=self.mesh.volume
        self.is_convex=self.mesh.is_convex
        
        # self.centroid=self.mesh.centroid
        # self.center_mass=self.mesh.center_mass
        # self.moment_inertia=self.mesh.moment_inertia
        
    def get_feature_data(self):
        if self.mesh is None:
            print("mesh is not loaded")
            return None
        data = [
            {
            'FeatureType':'Geometry',
            'FeatureName':'Dimension',
            'FeatureDescription':'Calculated from OBB/MVBB, closest to the shape',
            'FeatureValue':self.dimensions.tolist()
            },
            {
            'FeatureType':'Geometry',
            'FeatureName':'OBBAxis',
            'FeatureDescription':'axes in global',
            'FeatureValue':self.axis.tolist(),
            },
            {
            'FeatureType':'Geometry',
            'FeatureName':'ExtrudedAxis',
            'FeatureDescription':'the major axis or not equal dimension',
            'FeatureValue':self.extruded_axis.tolist(),
            },
            {
            'FeatureType':'Geometry',
            'FeatureName':'ExtrusionLength',
            'FeatureDescription':'the major axis or not equal dimension',
            'FeatureValue':self.extruded_length,
            },
            {
            'FeatureType':'Geometry',
            'FeatureName':'IsConvex',
            'FeatureDescription':'convex?',
            'FeatureValue': self.is_convex,
            },
            {
            'FeatureType':'Geometry',
            'FeatureName':'Volume',
            'FeatureDescription':'gross volume',
            'FeatureValue':self.volume,
            },
            {
            'FeatureType':'Geometry',
            'FeatureName':'Min',
            'FeatureDescription':'min point in global',
            'FeatureValue':self.min.tolist()
            },
            {
            'FeatureType':'Geometry',
            'FeatureName':'Max',
            'FeatureDescription':'max point in global',
            'FeatureValue':self.max.tolist()
            },
            {
            'FeatureType':'Geometry',
            'FeatureName':'OBBCenter',
            'FeatureDescription':'Cooridnate in global',
            'FeatureValue':{
                'X':self.box_center[0],
                'Y':self.box_center[1],
                'Z':self.box_center[2],
                }
            },
            # {
            # 'FeatureType':'Geometry',
            # 'FeatureName':'Centroid',
            # 'FeatureDescription':'Cooridnate in global',
            # 'FeatureValue':{
            #     'X':self.centroid[0],
            #     'Y':self.centroid[1],
            #     'Z':self.centroid[2],
            #     }
            # },
            # {
            # 'FeatureType':'Geometry',
            # 'FeatureName':'CenterMass',
            # 'FeatureDescription':'center of mass, useful?',
            # 'FeatureValue':{
            #     'X':self.center_mass[0],
            #     'Y':self.center_mass[1],
            #     'Z':self.center_mass[2],
            #     }
            # },
            # {
            # 'FeatureType':'Geometry',
            # 'FeatureName':'IsWaterTight',
            # 'FeatureDescription':'very few cases not watertight',
            # 'FeatureValue':1 if self.mesh.is_watertight else False,
            # },
            # {
            # 'FeatureType':'Geometry',
            # 'FeatureName':'MomentInertia',
            # 'FeatureDescription':'useful?',
            # 'FeatureValue':{
            #     'X':self.moment_inertia[0],
            #     'Y':self.moment_inertia[1],
            #     'Z':self.moment_inertia[2],
            #     }
            # },
        ]
        return data
        
    def loadBVH(self,data):
        faces=data['Faces']
        vertices=data['Vertices']
        obj = fcl.BVHModel()
        obj.beginModel(1,1)
        for triangle in faces:
            obj.addTriangle(vertices[triangle[0]],vertices[triangle[1]],vertices[triangle[2]])
        obj.endModel()
        self.bvh=fcl.CollisionObject(obj)
    
    # check pairwise relationships:
    def is_parallel_axis(self, axis):
        return True if abs(np.dot(self.extruded_axis,axis))>math.cos(math.radians(self.threshhold_degree)) else False
    def is_parallel(self,obj):
        return self.is_parallel_axis(obj.extruded_axis)
        
    # check perpendicular relationships:
    def is_perpendicular_axis(self, axis):
        return True if abs(np.dot(self.extruded_axis,axis))<math.cos(math.radians(90-self.threshhold_degree)) else False
    def is_perpendicular(self,obj):
        return self.is_perpendicular_axis(obj.extruded_axis)

    def contact(self,obj):
        # 30 mm
        tolerance=30
        ret, result = fcl.distance(self.bvh, obj.bvh, cd.DistanceRequest(True))
        return True if ret<tolerance else False
        
    def is_higher(self,obj):
        return True if self.box_center[2]>obj.box_center[2] else False
    
    def higher_bottom(self,obj):
        return True if self.min[2]>obj.min[2] else False
        
    def longer(self,obj):
        return True if self.extruded_length>obj.extruded_length else False
        
    def bigger(self,obj):
        return True if self.volume>obj.volume else False
        
    def above(self,obj):
        return True if self.min[2]>obj.max[2] else False
        
    def overlapZ(self,obj):
        return True if self.min[2]<obj.max[2] and self.max[2]>obj.min[2] else False
        
    # three compare relative to the centroid of the whole model
    def closer_transverse(self,obj,center):
        return True if abs(self.box_center[0]-center[0])<abs(obj.box_center[0]-center[0]) else False
    def closer_longitudinal(self,obj,center):
        return True if abs(self.box_center[1]-center[1])<abs(obj.box_center[1]-center[1]) else False