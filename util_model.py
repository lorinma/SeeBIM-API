# Author: Dr. Ling Ma
# https://il.linkedin.com/in/cvlingma

import trimesh
import numpy as np
import math
from util_geom import Geom

class Model:
    def __init__(self,data=None,model_id=None):
        if data == None or model_id == None:
            self.model=None
            self.model_id=None
        else:
            self.model_id=model_id
            self.loadModel(data)
        
    def loadModel(self,data):
        self.model=list()
        self.guids=list()
        all_vertices=list()
        for it in data:
            self.model.append(Geom(it['Geometry']))
            self.guids.append(it['GlobalId'])
            all_vertices+=it['Geometry']['Vertices']
        self.model_center=np.amin(all_vertices,0)+np.amax(all_vertices,0)/2
    
    def get_geometry_features(self):
        if self.model==None:
            print("model is not loaded")
            return
        data=list()
        inx=0
        for obj in self.model:
            no_guid_data=obj.get_feature_data()
            with_guid_data=list()
            for no_guid_item in no_guid_data:
                no_guid_item['GlobalId']=self.guids[inx]
                no_guid_item['FileId']=self.model_id
                no_guid_item['FeatureProvider']="System"
                with_guid_data.append(no_guid_item)
            inx+=1
            data+=with_guid_data
        return data
    
    def get_pairwise_features(self):
        guids=np.array(self.guids)
        parallel_inx=list()
        objs=self.model
        obj_count=len(objs)
        remain_list=list(range(obj_count))
        data=list()
        for i in range(obj_count):
            if(not i in remain_list):
                continue
            new_parallel_group=list()
            new_parallel_group.append(i)
            for j in range(obj_count)[i+1:]:
                if(not j in remain_list):
                    continue
                if(objs[i].is_parallel(objs[j])):
                    new_parallel_group.append(j)
                    remain_list.remove(j)
            parallel_inx.append(new_parallel_group)
        
        parallel_candidate_list=list()
        for i in parallel_inx:
            parallel_candidate_list.append(i[0])
        remain_list=list(range(len(parallel_candidate_list)))
        perpendicular_pairs=list()
        for i in range(len(parallel_candidate_list)):
            for j in range(len(parallel_candidate_list))[i+1:]:
                if not j in remain_list or not i in remain_list:
                    continue
                if(objs[parallel_candidate_list[i]].is_perpendicular(objs[parallel_candidate_list[j]])):
                    remain_list.remove(i)
                    remain_list.remove(j)
                    perpendicular_pairs.append([i,j])
                    break
            if not i in remain_list:
                continue
        for para in parallel_inx:
            if len(para)>1:
                for i in para:
                    para_value=para[:]
                    para_value.remove(i)
                    data.append({
                            'GlobalId':guids[i],
                            'FeatureName':'Parallel',
                            'FeatureType':'Pairwise',
                            'FeatureProvider':'System',
                            'FeatureDescription':'',
                            'FeatureValue':guids[para_value].tolist(),
                            'FileId':self.model_id
                        })
        for perpendicular in perpendicular_pairs:
            obj1=parallel_inx[perpendicular[0]]
            obj2=parallel_inx[perpendicular[1]]
            for i in obj1:
                data.append({
                        'GlobalId':guids[i],
                        'FeatureName':'Perpendicular',
                        'FeatureType':'Pairwise',
                        'FeatureProvider':'System',
                        'FeatureDescription':'',
                        'FeatureValue':guids[obj2].tolist(),
                        'FileId':self.model_id
                    })
            for i in obj2:
                data.append({
                        'GlobalId':guids[i],
                        'FeatureName':'Perpendicular',
                        'FeatureType':'Pairwise',
                        'FeatureProvider':'System',
                        'FeatureDescription':'',
                        'FeatureValue':guids[obj1].tolist(),
                        'FileId':self.model_id
                    })
                    
        contact_dict=dict()
        for guid in guids:
            contact_dict[guid]=list()
        for i in range(obj_count):
            for j in range(obj_count)[i+1:]:
                if objs[i].contact(objs[j]):
                    contact_dict[guids[i]].append(j)
                    contact_dict[guids[j]].append(i)
        for key in contact_dict:
            if len(contact_dict[key])==0:
                continue
            data.append({
                    'GlobalId':key,
                    'FeatureName':'Contact',
                    'FeatureType':'Pairwise',
                    'FeatureProvider':'System',
                    'FeatureDescription':'',
                    'FeatureValue':guids[contact_dict[key]].tolist(),
                    'FileId':self.model_id
                })
        return data
        
    def get_features(self):
        return self.get_geometry_features()+self.get_pairwise_features()
    
    def get_features_from_dropbox_link(self,url,model_id):
        from util_io import IO
        from util_ifc import IFC
        file=IO()
        file_path=file.save_file(url)
        ifc=IFC(file_path)
        data=ifc.parse_geometry()
        self.loadModel(data)
        self.model_id=model_id
        data=self.get_features()
        file.remove_file(file_path)
        return data