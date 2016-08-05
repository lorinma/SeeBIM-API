# Author: Ling Ma
# https://il.linkedin.com/in/cvlingma

import os
from eve.io.mongo import Validator
import requests
import json
import schema
from eve.methods.get import get_internal,getitem_internal
from eve.methods.delete import deleteitem_internal
from eve.methods.post import post_internal
from eve.methods.patch import patch_internal
from flask import abort
from bson.objectid import ObjectId

import numpy as np
import math

from os.path import join, dirname
from dotenv import load_dotenv
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

# use default account for get trimble token
trimble_url=os.environ.get('TRIMBLE_API_URL')
trimble_email=os.environ.get('TRIMBLE_EMAIL')
trimble_key=os.environ.get('TRIMBLE_KEY')
def get_trimble_token():
    para={'emailAddress':trimble_email, 'key':trimble_key}
    headers={"Content-Type":"application/json"}
    r = requests.post(trimble_url+'auth',data=json.dumps(para),headers=headers)
    return r.json()['token']

from ifcutil import IFC
from utils import Util

from geom import Geom
import trimesh

from eve import Eve
app = Eve()
# app = Eve(settings='settings.py')


import gspread
from oauth2client.service_account import ServiceAccountCredentials

###########################################
# add user
def add_user(items):
    for item in items:
        item['trimble_email']=trimble_email
        item['trimble_key']=trimble_key
def remove_dup_user(items):
    for item in items:
        dups = get_internal('user',**{'firebase_uid': item['firebase_uid']})[0]['_items']
        if len(dups)>1:
            deleteitem_internal('user',**{'_id': item['_id']})
app.on_insert_user+=add_user
app.on_inserted_user+=remove_dup_user

###########################################
# add project, first to trimble, then to mongo
def add_project(items):
    token = get_trimble_token()
    for item in items:
        item['user_id'] = get_user_by_firebase_uid(item['firebase_uid'])['_id']
        para={"name": item['name'],"description": item['description']}
        headers={"Content-Type":"application/json","Authorization":"Bearer "+token}
        r = requests.post(trimble_url+'projects',data=json.dumps(para),headers=headers)
        data=r.json()
        item['trimble_project_id']=data['id']
        item['trimble_root_folder_id']=data['rootId']
        item['trimble_server_region']=data['location']
        item['trimble_root_folder_id']=data['rootId']
app.on_insert_project+=add_project
def get_project_by_id(_id):
    return getitem_internal('project',**{'_id': _id})[0]

###########################################
# add file, first to trimble, then to mongo
def get_user_by_firebase_uid(firebase_uid):
    return getitem_internal('user',**{'firebase_uid': firebase_uid})[0]
def add_file_to_trimble(items):
    tool=Util()
    token = get_trimble_token()
    for item in items:
        item['user_id']=get_user_by_firebase_uid(item['firebase_uid'])
        project_info = get_project_by_id(item['project_id'])
        item['trimble_folder_id']=project_info['trimble_root_folder_id']
        item['trimble_project_id']=project_info['trimble_project_id']
        
        # save file 
        file_path=tool.save_file(item['source_url'])

        para={"parentId": item['trimble_folder_id']}
        headers={"Authorization":"Bearer "+token}
        files = {'file': open(file_path, 'rb')}
        r = requests.post(trimble_url+'files?parentId='+item['trimble_folder_id'],files=files,headers=headers)
        data=r.json()[0]
        item['trimble_file_id']=data['id']
        item['trimble_version_id']=data['versionId']
        item['trimble_createdOn']=data['createdOn']
        item['trimble_modifiedOn']=data['modifiedOn']
        # finally remove the file
        tool.remove_file(file_path)
app.on_insert_file+=add_file_to_trimble

# get trimble file processing status
def get_file_status(item):
    token=get_trimble_token()
    headers={"Content-Type":"application/json","Authorization":"Bearer "+token}
    r = requests.get(trimble_url+'files/'+item['trimble_file_id']+'/status',headers=headers)
    item['status']=r.json()['status']
app.on_fetched_item_fileStatus+=get_file_status

# add entities to mongo
def add_file_to_mongo(items):
    file=IFC()
    for item in items:
        file_path=file.util.save_file(item['source_url'])
        # parse ifc and post to entity
        entity_data=file.parse_file(file_path,str(item['_id']))
        # the entity's attribute value could be list or string, so should skip the velidation
        post_internal('entity',entity_data,skip_validation=True)
        # parse ifc geometry
        entity_data=file.parse_geometry(file_path,str(item['_id']))
        # the oce brep data is for file format, so it's not good string, hence skip the validation
        post_internal('geometry',entity_data,skip_validation=True)
        # finally remove the file
        file.util.remove_file(file_path)
app.on_inserted_file+=add_file_to_mongo

###########################################
# get file with trimble token, file model viewer requires token
def get_trimble_file(item):
    item['trimble_token']=get_trimble_token()
app.on_fetched_item_fileTrimble+=get_trimble_file

###########################################
# pairwise feature checking
def connectChecking(my_mesh, mesh):
    my_bound=my_mesh.mesh.bounds.reshape(1,6)[0]
    my_tree=my_mesh.mesh.triangles_tree()
    bound=mesh.mesh.bounds
    bound=np.array([bound[0].dot(0.99).tolist(),bound[1].dot(1.01).tolist()]).reshape(1,6)[0]
    potential_triangle_indices=list(my_tree.intersection(bound))
    if len(potential_triangle_indices)>0:
        return 1
    else:
        return -1
def parallelChecking(my_mesh, mesh):
    threshhold_degree=5
    absolute_angle=math.degrees(math.acos(abs(np.dot(my_mesh.extruded_axis,mesh.extruded_axis))))
    if absolute_angle<threshhold_degree:
        return 1
    else:
        return -1
def higherCentroid(my_mesh, mesh):
    if my_mesh.centroid[2]>mesh.centroid[2]:
        return 1
    else:
        return -1
def lowerBottom(my_mesh, mesh):
    if my_mesh.min[2]<mesh.min[2]:
        return 1
    else:
        return -1
def longgerExtrusion(my_mesh, mesh):
    if my_mesh.length>mesh.length:
        return 1
    else:
        return -1
def bigger(my_mesh, mesh):
    if my_mesh.mesh.volume>mesh.mesh.volume:
        return 1
    else:
        return -1    
def above(my_mesh, mesh):
    if my_mesh.min[2]>mesh.max[2]:
        return 1
    else:
        return -1    
def closer_longitudinal(my_mesh, mesh,bridge_centroid):
    if abs(my_mesh.centroid[1]-bridge_centroid[1])<abs(mesh.centroid[1]-bridge_centroid[1]):
        return 1
    else:
        return -1
def closer_transverse(my_mesh, mesh,bridge_centroid):
    if abs(my_mesh.centroid[0]-bridge_centroid[0])<abs(mesh.centroid[0]-bridge_centroid[0]):
        return 1
    else:
        return -1
def overlapZ(my_mesh, mesh):
    if my_mesh.min[2]*1.01<mesh.max[2] and mesh.min[2]<my_mesh.max[2]*0.99:
        return 1
    else:
        return -1 
        
# add geometry and related features
def add_geometry(items):
    meshes=list()
    entityIds=list()
    globalIds=list()
    payload=list()
    
    bridge_min=list()
    bridge_max=list()
    for item in items:
        entity = getitem_internal('entity',**{"$and": [{"FileID":str(item["FileID"])},{"Attribute": {"$elemMatch":{"Value": str(item["GlobalId"]),"Name": "GlobalId"}}}]})[0]
        item['EntityID']=entity["_id"]
        entityIds.append(entity["_id"])
        globalIds.append(item["GlobalId"])
        # add features
        mesh=Geom(item['Geometry'])
        meshes.append(mesh)
        obb_features=mesh.getOBBFeature()
        for obb_feature in obb_features:
            payload.append({
                'FileID':str(item['FileID']),
                'GlobalId':str(item['GlobalId']),
                'EntityID':str(item['EntityID']),
                'Feature':obb_feature
            })
        shape_features=mesh.getMeshFeature()
        for shape_feature in shape_features:
            payload.append({
                'FileID':str(item['FileID']),
                'GlobalId':str(item['GlobalId']),
                'EntityID':str(item['EntityID']),
                'Feature':shape_feature
            })
        
        if len(bridge_min)==0:
            bridge_min=mesh.min
            bridge_max=mesh.max
        else:
            if bridge_min[0]>mesh.min[0]:
                bridge_min[0]=mesh.min[0]
            if bridge_min[1]>mesh.min[1]:
                bridge_min[1]=mesh.min[1]
            if bridge_min[2]>mesh.min[2]:
                bridge_min[2]=mesh.min[2]
                
            if bridge_max[0]<mesh.max[0]:
                bridge_max[0]=mesh.max[0]
            if bridge_max[1]<mesh.max[1]:
                bridge_max[1]=mesh.max[1]
            if bridge_max[2]<mesh.max[2]:
                bridge_max[2]=mesh.max[2]
                
    post_internal('geometryFeature',payload,skip_validation=True)
    # bridge_centroid=bridgeCentroid(meshes)
    bridge_centroid=[(bridge_min[0]+bridge_max[0])/2,(bridge_min[1]+bridge_max[1])/2,(bridge_min[2]+bridge_max[2])/2]
    print(len(entityIds))
    pair_payload=list()
    for i in range(len(entityIds)):
        my_mesh=meshes[i]
        my_id=entityIds[i]
        my_globalId=globalIds[i]
        
        connect_vector=list()
        para_vector=list()
        centorid_vector=list()
        bottom_vector=list()
        longger_vector=list()
        bigger_vector=list()
        above_vector=list()
        closer_longitudinal_vector=list()
        closer_transverse_vector=list()
        overlapZ_vector=list()
        
        for j in range(len(entityIds)):
            your_globalId=globalIds[j]
            if my_globalId==your_globalId:
                continue
            your_mesh=meshes[j]
            your_id=entityIds[j]

            connect_vector.append({'EntityID':your_id,'GlobalId':your_globalId,'Compare':connectChecking(my_mesh,your_mesh)})
            para_vector.append({'EntityID':your_id,'GlobalId':your_globalId,'Compare':parallelChecking(my_mesh,your_mesh)})
            centorid_vector.append({'EntityID':your_id,'GlobalId':your_globalId,'Compare':higherCentroid(my_mesh,your_mesh)})
            bottom_vector.append({'EntityID':your_id,'GlobalId':your_globalId,'Compare':lowerBottom(my_mesh,your_mesh)})
            longger_vector.append({'EntityID':your_id,'GlobalId':your_globalId,'Compare':longgerExtrusion(my_mesh,your_mesh)})
            bigger_vector.append({'EntityID':your_id,'GlobalId':your_globalId,'Compare':bigger(my_mesh,your_mesh)})
            above_vector.append({'EntityID':your_id,'GlobalId':your_globalId,'Compare':above(my_mesh,your_mesh)})
            closer_longitudinal_vector.append({'EntityID':your_id,'GlobalId':your_globalId,'Compare':closer_longitudinal(my_mesh,your_mesh,bridge_centroid)})
            closer_transverse_vector.append({'EntityID':your_id,'GlobalId':your_globalId,'Compare':closer_transverse(my_mesh,your_mesh,bridge_centroid)})
            overlapZ_vector.append({'EntityID':your_id,'GlobalId':your_globalId,'Compare':overlapZ(my_mesh,your_mesh)})
            
        pair_payload.append({'EntityID':my_id,'FileID':item['FileID'],'GlobalId':my_globalId,'Feature':{'Type':'Connect','Description':'either touching or collision','Vector':connect_vector}})
        pair_payload.append({'EntityID':my_id,'FileID':item['FileID'],'GlobalId':my_globalId,'Feature':{'Type':'Parallel','Description':'we are in parallel','Vector':para_vector}})
        pair_payload.append({'EntityID':my_id,'FileID':item['FileID'],'GlobalId':my_globalId,'Feature':{'Type':'HigherCentroid','Description':'I\'ve higher centroid','Vector':centorid_vector}})
        pair_payload.append({'EntityID':my_id,'FileID':item['FileID'],'GlobalId':my_globalId,'Feature':{'Type':'LowerBottom','Description':'I\'ve lower bottom','Vector':bottom_vector}})
        pair_payload.append({'EntityID':my_id,'FileID':item['FileID'],'GlobalId':my_globalId,'Feature':{'Type':'Longger','Description':'either touching or collision','Vector':longger_vector}})
        pair_payload.append({'EntityID':my_id,'FileID':item['FileID'],'GlobalId':my_globalId,'Feature':{'Type':'Bigger','Description':'bigger','Vector':bigger_vector}})
        pair_payload.append({'EntityID':my_id,'FileID':item['FileID'],'GlobalId':my_globalId,'Feature':{'Type':'Above','Description':'I\'ve higher centroid','Vector':above_vector}})
        pair_payload.append({'EntityID':my_id,'FileID':item['FileID'],'GlobalId':my_globalId,'Feature':{'Type':'CloserLongitudinal','Description':'closer_longitudinal_vector','Vector':closer_longitudinal_vector}})
        pair_payload.append({'EntityID':my_id,'FileID':item['FileID'],'GlobalId':my_globalId,'Feature':{'Type':'CloserTransverse','Description':'closer_transverse_vector','Vector':closer_transverse_vector}})
        pair_payload.append({'EntityID':my_id,'FileID':item['FileID'],'GlobalId':my_globalId,'Feature':{'Type':'OverlapZ','Description':'overlapZ_vector','Vector':overlapZ_vector}})
    post_internal('pairwiseFeature',pair_payload,skip_validation=True)
app.on_insert_geometry+=add_geometry

###########################################
# entity with shape and feature

def get_item_with_shape(item):
    # TODO here needs to take care of pagination when they are more than 1 page
    geoms = get_internal('geometry',**{"EntityID":item["_id"]})[0]['_items']
    if len(geoms)>0:
        # an product will have no more than 1 geom
        item['Geometry']=geoms[0]['Geometry']
    features = get_internal('geometryFeature',**{"EntityID":item["_id"]})[0]['_items']
    if len(features)>0:
        item['Features']=list()
        # an product will have no more than 1 geom
        for feature in features:
            item['Features'].append(feature['Feature'])
    pairFeatures = get_internal('pairwiseFeature',**{"EntityID":item["_id"]})[0]['_items']
    if len(features)>0:
        item['PairwiseFeature']=list()
        # an product will have no more than 1 geom
        for pairFeature in pairFeatures:
            item['PairwiseFeature'].append(pairFeature['Feature'])
def get_source_with_shape(data):
    items=data['_items']
    for item in items:
        get_item_with_shape(item)  
app.on_fetched_item_entityGeomFeature+=get_item_with_shape
app.on_fetched_source_entityGeomFeature+=get_source_with_shape

###########################################
# model's features

# shape feature of all the elements
def get_item_modelShapeFeatures(item):
    # locate the spreadsheet
    scope = ['https://spreadsheets.google.com/feeds']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('seebim-credential.json', scope)
    gc = gspread.authorize(credentials)
    wks = gc.open("toy bridge of SeeBIM - Feature matching")

    # fetch the knowledge data
    Knowledge = wks.worksheet("Shape Feature Knowledge")
    knowledge_data=Knowledge.get_all_values()
    elements=list()
    knowledge_shape_norm_matrix=list()
    headings=knowledge_data[0][1:]
    for it in knowledge_data[1:]:
        elements.append(it[0])
        v = np.array(it[1:], dtype='|S4').astype(np.float)
        norm=np.linalg.norm(v)
        norm_vector=list()
        if(norm==0):
            norm_vector=np.zeros(len(v))
        else:
            norm_vector=np.divide(v,norm).tolist()
        knowledge_shape_norm_matrix.append(norm_vector)
    
    # process the feature data    
    app.config['DOMAIN']['geometryFeature']['pagination'] = False
    features = get_internal('geometryFeature',**{"FileID":item["_id"]})[0]['_items']
    app.config['DOMAIN']['geometryFeature']['pagination'] = True
    
    facts=dict()
    for feature in features:
        if feature['GlobalId'] in facts:
            facts[feature['GlobalId']][feature['Feature']['Name']]=feature['Feature']['Value']
        else:
            facts[feature['GlobalId']]={feature['Feature']['Name']:feature['Feature']['Value']}

    # fill the fact data
    fact_shape_norm_matrix=list()
    fact_sheet = wks.worksheet("Shape Feature Fact")
    # fact_sheet.resize(1,fact_sheet.col_count)
    parameters=fact_sheet.get_all_values()[0][1:]
    object_list=list()
    for key in facts:
        vector=list()
        for para in parameters:
            vector.append(facts[key][para])
        norm=np.linalg.norm(vector)   
        norm_vector=np.divide(vector,norm).tolist() 
        fact_shape_norm_matrix.append(norm_vector)
        object_list.append(key)
        # vector.insert(0,key)
        # fact_sheet.append_row(vector)
    
    # dot product
    products=np.dot(fact_shape_norm_matrix,np.transpose(knowledge_shape_norm_matrix))
    
    # # fill the matching result
    # worksheet_matching = wks.worksheet("Shape Feature Matching")
    # # there list candidate in decending
    # worksheet_matching.resize(1,len(elements)*2+1)
    # result with entityID as the key
    for j in range(len(object_list)):
        # data=products[j].tolist()
        # candidates=np.array(elements)[np.argsort(data)[::-1]].tolist()
        data=products[j]
        candidates=np.array(elements)
        distinct_decent=np.sort(np.unique(data))[::-1]
        top_list=list()
        # number of elements return
        count = 2 
        for i in range(count):
            decent_utility_index=np.argwhere(data==distinct_decent[i])
            decent_utility_index=decent_utility_index.reshape(1,decent_utility_index.size)[0].tolist()
            # print(decent_utility_index)
            top_list+=decent_utility_index
            if len(top_list)>=count:
                break
        top_candidates=candidates[top_list]
        top_data=data[top_list]
        properties=list()
        for i in range(len(top_list)):
            properties.append({
                'Name':top_candidates[i],
                'Description':'Similarity score',
                'Value':top_data[i]
            })
        # utility_value=np.sort(data)[::-1]
        # np.argwhere(a==max(a))
        user_property={
            'Name':'Geometry-based classification',
            'Description':'Object classification based on how similar the geometry is',
            'Children': properties
        }
        update_user_property(object_list[j],user_property,item['_id'])
        # data=np.concatenate((data,candidates),axis=0).tolist()
        # data.insert(0,object_list[j])
        # worksheet_matching.append_row(data)
    return products
app.on_fetched_item_modelShapeFeature+=get_item_modelShapeFeatures

def get_item_modelPairFeature(item):
    # locate the spreadsheet
    scope = ['https://spreadsheets.google.com/feeds']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('seebim-credential.json', scope)
    gc = gspread.authorize(credentials)
    wks = gc.open("toy bridge of SeeBIM - Feature matching")

    # fetch the knowledge data
    Knowledge = wks.worksheet("Pairwise Knowledge")
    knowledge_data=Knowledge.get_all_values()
    relations=list()
    parameters=knowledge_data[0][1:]
    knowledge_shape_norm_matrix=list()
    element_list=list()
    for it in knowledge_data[1:]:
        rel=it[0].split(",")
        relations.append({
            rel[0]:rel[1]
        })
        v = np.array(it[1:], dtype='|S4').astype(np.float)
        norm=np.linalg.norm(v)
        norm_vector=list()
        if(norm==0):
            norm_vector=np.zeros(len(v))
        else:
            norm_vector=np.divide(v,norm).tolist()
        knowledge_shape_norm_matrix.append(norm_vector)
        # gather all the elements
        if rel[0] not in element_list:
            element_list.append(rel[0])
            
    app.config['DOMAIN']['pairwiseFeature']['pagination'] = False
    pairs = get_internal('pairwiseFeature',**{"FileID":item["_id"]})[0]['_items']
    app.config['DOMAIN']['pairwiseFeature']['pagination'] = True
    
    app.config['DOMAIN']['geometry']['pagination'] = False
    entities = get_internal('geometry',**{"FileID":item["_id"]})[0]['_items']
    app.config['DOMAIN']['geometry']['pagination'] = True
    # reorganize the data dict
    pair_facts=dict()
    for pair in pairs:
        guid=pair['GlobalId']
        type=pair['Feature']['Type']
        vector=pair['Feature']['Vector']
        for i in vector:
            cell=i['Compare']
            obj=i['GlobalId']
            data={guid:{obj:{type:cell}}}
            if guid not in pair_facts:
                pair_facts[guid]=data[guid]
                continue
            if obj not in pair_facts[guid]:
                pair_facts[guid][obj]=data[guid][obj]
                continue
            if type not in pair_facts[guid][obj]:
                pair_facts[guid][obj][type]=data[guid][obj][type]
                continue
    # reshape the dict to 2d list
    object_list=list()
    fact_sheet = wks.worksheet("Pairwise Fact")
    # fact_sheet.resize(1,fact_sheet.col_count)
    norm_fact_matrix=list()
    for entity1 in entities:
        guid1=entity1['GlobalId']
        # get all the objects
        object_list.append(guid1)
        for entity2 in entities:
            guid2=entity2['GlobalId']
            if guid1==guid2:
                continue
            vector=list()
            for para in parameters:
                vector.append(pair_facts[guid1][guid2][para])
            norm=np.linalg.norm(vector)
            norm_vector=list()
            norm_vector=np.divide(vector,norm).tolist()
            norm_fact_matrix.append(norm_vector)
            # append row to gsheet
            vector.insert(0,guid1+','+guid2)
            # fact_sheet.append_row(vector)
    # dot product

    matrix=np.dot(norm_fact_matrix,np.transpose(knowledge_shape_norm_matrix))
    
    # # fill the matching result
    # worksheet_matching = wks.worksheet("Pairwise Matching")
    # # there list candidate in decending
    # worksheet_matching.resize(1,worksheet_matching.col_count)
    # matrix_inx=0
    # for entity1 in entities:
    #     guid1=entity1['GlobalId']
    #     for entity2 in entities:
    #         guid2=entity2['GlobalId']
    #         if guid1==guid2:
    #             continue
    #         vector=matrix[matrix_inx].tolist()
    #         matrix_inx+=1
    #         vector.insert(0,guid1+','+guid2)
    #         # append row to matching result
    #         worksheet_matching.append_row(vector)
    
    # find the indices of interesting ranges and sum to form a cell of the matching matrix
    object_count=len(object_list)
    element_count=len(element_list)
    match_matrix=list()
    match_matrix_direct=list()
    for object_list_index in range(len(object_list)):
        match_vector=list()
        for element_list_index in range(len(element_list)):
            object_index=object_list_index*(object_count-1)
            element_index=element_list_index*(element_count)
            rows=matrix[object_index:object_index+object_count-1]
            my_range1=rows.transpose()[element_index:element_index+element_count].transpose()

            obj_index=list()
            for i in range(object_list_index):
                obj_index.append(i*(object_count-1)+object_list_index-1)
            for i in range(object_list_index+1,object_count,1):
                obj_index.append(i*(object_count-1)+object_list_index)
            ele_index=list()
            for i in range(element_list_index+1):
                ele_index.append(i*(element_count)+element_list_index)
            for i in range(element_list_index+1,element_count,1):
                ele_index.append(i*(element_count)+element_list_index)
            my_range2=matrix[obj_index].transpose()[ele_index].transpose()
            match_vector.append(my_range1.sum()+my_range2.sum())
            
        # normalize the result
        norm=np.linalg.norm(match_vector)
        norm_vector=list()
        if(norm==0):
            norm_vector=np.zeros(len(match_vector))
        else:
            norm_vector=np.divide(match_vector,norm).tolist()
        match_matrix.append(norm_vector)
        match_matrix_direct.append(match_vector)
        # match_matrix.append(match_vector)
    
    # # fill the matching result
    # worksheet_matching_result = wks.worksheet("Pairwise Matching Processed")
    # # there list candidate in decending
    # worksheet_matching_result.resize(1,worksheet_matching_result.col_count)
    # matrix_inx=0
    # for entity in entities:
        # candidates=np.array(element_list)[np.argsort(data)[::-1]].tolist()
    #     guid=entity['GlobalId']
    #     vector=match_matrix[matrix_inx]
    #     matrix_inx+=1
    #     vector.insert(0,guid)
    #     # append row to matching result
    #     worksheet_matching_result.append_row(vector)
        # data=np.concatenate((data,candidates),axis=0).tolist()
        # data.insert(0,object_list[j])
        # worksheet_matching.append_row(data)
    
    # fill the matching result
    # result with entityID as the key
    for j in range(len(object_list)):
        data=np.array(match_matrix[j])
        candidates=np.array(element_list)
        # update_user_property(object_list[j],{
        #     'Name':'Pairwise-based',
        #     'Description':'Enrichment result',
        #     'Value': str(candidates)+str(np.sort(data)[::-1])
        # },item['_id'])
        
        distinct_decent=np.sort(np.unique(data))[::-1]
        top_list=list()
        # number of elements return
        count = 2 
        for i in range(count):
            decent_utility_index=np.argwhere(data==distinct_decent[i])
            decent_utility_index=decent_utility_index.reshape(1,decent_utility_index.size)[0].tolist()
            # print(decent_utility_index)
            top_list+=decent_utility_index
            if len(top_list)>=count:
                break
        top_candidates=candidates[top_list]
        top_data=data[top_list]
        properties=list()
        for i in range(len(top_list)):
            properties.append({
                'Name':top_candidates[i],
                'Description':'Similarity score',
                'Value':top_data[i]
            })
        # utility_value=np.sort(data)[::-1]
        # np.argwhere(a==max(a))
        user_property={
            'Name':'Pairwise-based classification',
            'Description':'Object classification based on pairwise spatial relationship',
            'Children': properties
        }
        update_user_property(object_list[j],user_property,item['_id'])
        
    return match_matrix
app.on_fetched_item_modelPairFeature+=get_item_modelPairFeature

def get_item_run(item):
    pair_match_matrix=get_item_modelPairFeature(item)
    fact_shape_norm_matrix=get_item_modelShapeFeatures(item)
    # average? square root?
app.on_fetched_item_run+=get_item_run

def get_item_clear(item):
    app.config['DOMAIN']['geometry']['pagination'] = False
    entities = get_internal('geometry',**{"FileID":item["_id"]})[0]['_items']
    app.config['DOMAIN']['geometry']['pagination'] = True
    # clean enrichment fields if any
    for entity in entities:
        entity_data=getitem_internal('entity',**{'_id': entity['EntityID']})[0]
        if 'UserProperty' in entity_data and len(entity_data['UserProperty'])>0:
            payload={'UserProperty':entity_data['UserProperty']}
            for p_set in payload['UserProperty']:
                if p_set['Name']=='Enrichment' and len(p_set['Children'])>0:
                    for p in p_set['Children']:
                        if p['Name']=='Geometry-based' or p['Name']=='Pairwise-based':
                            p['Value']=''
        else:
            payload={
                'UserProperty':[{
                    'Name':'Enrichment',
                    'Description':'Enrichment results',
                    'Children':[
                    {
                        'Name':'Geometry-based',
                        'Description':'Enrichment result',
                        'Value':'',
                    },
                    {
                        'Name':'Pairwise-based',
                        'Description':'Enrichment result',
                        'Value':'',
                    }],
                }]
            }
        patch_internal('entity',payload,**{'_id': entity['EntityID']})
    # pair_match_matrix=get_item_modelPairFeature(item)
    # average? square root?
app.on_fetched_item_clear+=get_item_clear

###########################################
# update an entity

def update_user_property(guid,data,file_id):
    entity_data=getitem_internal('entity',**{"FileID":file_id,"Attribute": {"$elemMatch":{"Value": guid,"Name": "GlobalId"}}})[0]
    if 'UserProperty' in entity_data and len(entity_data['UserProperty'])>0:
        payload={'UserProperty':entity_data['UserProperty']}
        hasMe=False
        for p_set in payload['UserProperty']:
            if p_set['Name']==data['Name']:
                hasMe=True
                break
        if not hasMe:
            payload['UserProperty'].append(data)
    else:
        payload={
            'UserProperty':[data]
        }
    # print(payload)
    patch_internal('entity',payload,**{'_id': entity_data['_id']})

# # only return documents that have property sets, 
# # however, ifcobject will start having properties, so potentially there're many
# # in addition, an ifcproduct may not have property, then it is unexpectedly removed from the list
# def pre_get_entity_geom_feature(request, lookup):
#     lookup["PropertySets"] = {'$exists': True}
# app.on_pre_GET_entityGeomFeature += pre_get_entity_geom_feature

###########################################
# entity with features

# # get all shape features of this element
# def get_item_entityShapeFeatures(item):
#     vertical = getitem_internal('Vertical',**{"_id":item["_id"]})[0]
#     item['ShapeFeatures']={
#         'ParallelBridgeLongitudinal':getitem_internal('parallelBridge',**{"_id":item["_id"]})[0]['Compare']['Vector'][0]['Compare'],
#         'ParallelBridgeTransverse':getitem_internal('paraBriTrans',**{"_id":item["_id"]})[0]['Compare']['Vector'][0]['Compare'],
#         'Vertical':vertical['Compare']['Vector'][0]['Compare'],
#         'Convex':getitem_internal('convex',**{"_id":item["_id"]})[0]['Compare']['Vector'][0]['Compare'],
#     }
#     item['GlobalId']=vertical['Compare']['Vector'][0]['GlobalId']
# app.on_fetched_item_entityShapeFeatures+=get_item_entityShapeFeatures

# # get all pair features of this element
# def get_item_entityPairFeatures(item):
#     app.config['DOMAIN']['geometry']['pagination'] = False
#     others=get_internal('geometry',**{"EntityID":{'$ne':item["_id"]}})[0]['_items']
#     featurs=['Contact','Parallel extrusion','Higher centroid', 'Lower bottom',	'Longger extrusion',	'Bigger',	'Complete above',	'Closer to transverse axis',	'Closer to longitudinal axis',	'Overlap in z']
#     my_globalid=getitem_internal('geometry',**{"EntityID":item["_id"]})[0]['GlobalId']
#     GlobalIds=list()
#     for other in others:
#         GlobalIds.append({
#             my_globalid:other['GlobalId']
#             }
#         )
        
#     app.config['DOMAIN']['geometry']['pagination'] = True
#     data=dict()
#     matrix=list()
#     vector=list()
    
#     connect = getitem_internal('connect',**{"_id":item["_id"]})[0]['Compare']['Vector']
#     for it in connect:
#         data[it['EntityID']]=it['Compare']
#     for other in others:
#         vector.append(data[other['EntityID']])
#     matrix.append(vector)
    
#     paraExtrusion = getitem_internal('paraExtrusion',**{"_id":item["_id"]})[0]['Compare']['Vector']
#     for it in paraExtrusion:
#         data[it['EntityID']]=it['Compare']
#     for other in others:
#         vector.append(data[other['EntityID']])
#     matrix.append(vector)
    
#     higherCentroid = getitem_internal('higherCentroid',**{"_id":item["_id"]})[0]['Compare']['Vector']
#     for it in higherCentroid:
#         data[it['EntityID']]=it['Compare']
#     for other in others:
#         vector.append(data[other['EntityID']])
#     matrix.append(vector)
    
#     lowerBottom = getitem_internal('lowerBottom',**{"_id":item["_id"]})[0]['Compare']['Vector']
#     for it in lowerBottom:
#         data[it['EntityID']]=it['Compare']
#     for other in others:
#         vector.append(data[other['EntityID']])
#     matrix.append(vector)
    
#     longgerExtrusion = getitem_internal('longgerExtrusion',**{"_id":item["_id"]})[0]['Compare']['Vector']
#     for it in longgerExtrusion:
#         data[it['EntityID']]=it['Compare']
#     for other in others:
#         vector.append(data[other['EntityID']])
#     matrix.append(vector)
    
#     volumeBigger = getitem_internal('volumeBigger',**{"_id":item["_id"]})[0]['Compare']['Vector']
#     for it in volumeBigger:
#         data[it['EntityID']]=it['Compare']
#     for other in others:
#         vector.append(data[other['EntityID']])
#     matrix.append(vector)
    
#     completeAbove = getitem_internal('completeAbove',**{"_id":item["_id"]})[0]['Compare']['Vector']
#     for it in completeAbove:
#         data[it['EntityID']]=it['Compare']
#     for other in others:
#         vector.append(data[other['EntityID']])
#     matrix.append(vector)
    
#     closerTran = getitem_internal('closerTran',**{"_id":item["_id"]})[0]['Compare']['Vector']
#     for it in closerTran:
#         data[it['EntityID']]=it['Compare']
#     for other in others:
#         vector.append(data[other['EntityID']])
#     matrix.append(vector)
    
#     closerLongi = getitem_internal('closerLongi',**{"_id":item["_id"]})[0]['Compare']['Vector']
#     for it in closerLongi:
#         data[it['EntityID']]=it['Compare']
#     for other in others:
#         vector.append(data[other['EntityID']])
#     matrix.append(vector)
    
#     overlapZ = getitem_internal('overlapZ',**{"_id":item["_id"]})[0]['Compare']['Vector']
#     for it in overlapZ:
#         data[it['EntityID']]=it['Compare']
#     for other in others:
#         vector.append(data[other['EntityID']])
#     matrix.append(vector)
    
#     t_matrix=np.transpose(matrix)
#     matrix_norm=list()
#     for v in t_matrix:
#         norm=np.linalg.norm(v)
#         norm_vector=list()
#         if(norm==0):
#             norm_vector=[0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0]
#         else:
#             norm_vector=np.divide(v,norm).tolist()
#         matrix_norm.append(norm_vector)
#     item["Matrix"]=matrix_norm
#     item["Relations"]=GlobalIds
#     item['Features']=featurs
#     item['GlobalId']=my_globalid
# app.on_fetched_item_entityPairFeatures+=get_item_entityPairFeatures


# ###########################################
# # below are old staff
# ###########################################

# # ###########################################
# # # deletion, this is not a good idea

# # # delete entity 
# # def delete_entity(item):
# #     geometries=get_internal('geometry',**{'EntityID': item["_id"]})[0]["_items"]
# #     for geometry in geometries:
# #         deleteitem_internal('geometry',**{"_id":geometry['_id']})
# #     app.config['DOMAIN']['geometryFeature']['pagination'] = False
# #     features=get_internal('geometryFeature',**{'EntityID': item["_id"]})[0]["_items"]
# #     for feature in features:
# #         deleteitem_internal('geometryFeature',**{"_id":feature['_id']})
# #     app.config['DOMAIN']['geometryFeature']['pagination'] = True
# # def delete_all_entity():
# #     items = get_internal('entity')[0]['_items']
# #     for item in items:
# #         delete_entity(item)
# # app.on_delete_item_entity+=delete_entity
# # app.on_delete_resource_entity+=delete_all_entity

# # # delete file 
# # def delete_file(item):
# #     app.config['DOMAIN']['entity']['pagination'] = False
# #     entities=get_internal('entity',**{'FileID': item["_id"]})[0]["_items"]
# #     for entity in entities:
# #         deleteitem_internal('entity',**{"_id":entity['_id']})
# #     app.config['DOMAIN']['entity']['pagination'] = True
# # def delete_all_file():
# #     app.config['DOMAIN']['entity']['pagination'] = False
# #     entities=get_internal('entity')[0]["_items"]
# #     for entity in entities:
# #         deleteitem_internal('entity',**{"_id":entity['_id']})
# #     app.config['DOMAIN']['entity']['pagination'] = True
# # # don't want the web interface to delete too slow
# # app.on_delete_item_file+=delete_file
# # app.on_delete_resource_file+=delete_all_file

# # # interaction with entity attributes
# # def get_attribute_value(attributes,attribute_name):
# #     for attribute in attributes:
# #         if attribute['Name']==attribute_name:
# #             return attribute['Value']
# #     print("No such attribute")
# #     return None
# # def set_attribute_value(attributes,attribute_name,value):
# #     for attribute in attributes:
# #         if attribute['Name']==attribute_name:
# #             attribute['Value']=value
# #     return attributes
    
# # # entity property set interaction
# # def get_item_property_set(item):
# #     properties=get_attribute_value(item['Attribute'],'HasProperties')
# #     if properties is None:
# #         return
# #     # if the attribute like HasProperties only has 1 node, then it is a str instead of list
# #     if isinstance(properties,str):
# #         properties=[properties]
# #     properties_data=list()
# #     for property in properties:
# #         try:
# #             property_data=getitem_internal('entitySimple',**{"_id":property})
# #             properties_data.append(property_data[0])
# #         except:
# #             print("No such property")
# #     if len(properties_data)>0:
# #         item['Properties']=properties_data
# # def get_property_set(data):
# #     items=data['_items']
# #     for item in items:
# #         get_item_property_set(item)        
# # app.on_fetched_item_entityPropertySet+=get_item_property_set  
# # app.on_fetched_resource_entityPropertySet+=get_property_set

# # # reldefined
# # def get_item_rel_property_set(item):
# #     # do we really need try here?
# #     try:
# #         property_set_id=get_attribute_value(item['Attribute'],'RelatingPropertyDefinition')
# #         if property_set_id is not None:
# #             p_set=getitem_internal('entityPropertySet',**{"_id":ObjectId(property_set_id)})[0]
# #             item['PropertySet']=p_set
# #     except:
# #         print("no property set linked in this relation")
# # def get_rel_property_set(data):
# #     items=data['_items']
# #     for item in items:
# #         get_item_rel_property_set(item)  
# # app.on_fetched_item_entityRelProperties+=get_item_rel_property_set
# # app.on_fetched_resource_entityRelProperties+=get_rel_property_set

# # # entity with property set interaction
# # # you can only query specific entity item
# # def get_item_with_property(item):
# #     rels = get_internal('entityRelProperties',**{"Attribute": {"$elemMatch":{"Value": str(item['_id']),"Name": "RelatedObjects"}}})[0]['_items']
# #     if len(rels)>0:
# #         item['PropertyDefinition']=rels
# #     shape_feature = getitem_internal('geometryWithFeature',**{"EntityID":item["_id"]})[0]
# #     item['Geometry']=shape_feature['Geometry']
# #     features=list()
# #     for feature in shape_feature['Features']:
# #         features.append(feature)
# #     item['Features']=features
# # def get_resource_with_property(data):
# #     items=data['_items']
# #     for item in items:
# #         get_item_with_property(item)  
# # app.on_fetched_item_entityWithProperty+=get_item_with_property
# # app.on_fetched_resource_entityWithProperty+=get_resource_with_property

# # # shape and feature
# # def get_item_shape_with_feature(item):
# #     features = get_internal('geometryFeature',**{"GeometryID":item["_id"]})[0]['_items']
# #     if len(features)>0:
# #         item['Features']=list()
# #         for feature in features:
# #             item['Features'].append(feature['Feature'])
# #     else:
# #         item['Features']=list()
# #         mesh=Geom(item['Geometry'])
# #         payload=list()
# #         obb_features=mesh.getOBB()
# #         shape_features=mesh.getMeshFeature()
# #         data=dict()
# #         for obb_feature in obb_features:
# #             payload.append({
# #                 'FileID':str(item['FileID']),
# #                 'GlobalId':str(item['GlobalId']),
# #                 'EntityID':str(item['EntityID']),
# #                 'GeometryID':str(item['_id']),
# #                 'Feature':obb_feature
# #             })
# #             item['Features'].append(obb_feature)
# #         for shape_feature in shape_features:
# #             payload.append({
# #                 'FileID':str(item['FileID']),
# #                 'GlobalId':str(item['GlobalId']),
# #                 'EntityID':str(item['EntityID']),
# #                 'GeometryID':str(item['_id']),
# #                 'Feature':shape_feature
# #             })
# #             item['Features'].append(shape_feature)
# #         post_internal('geometryFeature',payload,skip_validation=True)
# # def get_resource_shape_with_feature(data):
# #     items=data['_items']
# #     for item in items:
# #         get_item_shape_with_feature(item)  
# # def delete_geometry(item):
# #     while 1:
# #         features=get_internal('geometryFeature',**{'GeometryID': item["_id"]})[0]["_items"]
# #         if len(features)<1:
# #             break
# #         for feature in features:
# #             deleteitem_internal('geometryFeature',**{"_id":feature['_id']})

# # def delete_all_geometry():
# #     items = get_internal('geometry')[0]['_items']
# #     for item in items:
# #         delete_geometry(item)
# # app.on_fetched_item_geometryWithFeature+=get_item_shape_with_feature
# # app.on_fetched_resource_geometryWithFeature+=get_resource_shape_with_feature

# # app.on_delete_item_geometry+=delete_geometry
# # app.on_delete_resource_geometry+=delete_all_geometry

# # def getFeature(item,feature_name):
# #     features=item['Features']
# #     for feature in features:
# #         if feature['Name']==feature_name:
# #             return feature['Value']
# #     return None
    
# # # Bug: cannot fetch these extra items, even not print 
# # # def get_item_feature_entity(item):
# # #     print("ol1")
# # #     entity = getitem_internal('entityWithProperty',**{"_id":item["EntityID"]})[0]
# # #     print(entity)
# # #     item['Entity']=entity
# # # def get_source_feature_entity(data):
# # #     print("data")
# # #     items=data['_items']
# # #     print("ol")
# # #     for item in items:
# # #         get_item_feature_entity(item)  
# # # app.on_fetched_item_geometryFeature+=get_item_feature_entity
# # # app.on_fetched_source_geometryFeature+=get_source_feature_entity

# # # query
# # def get_item_query(item):
# #     query=dict()
# #     query["$and"]=list()
# #     query['$and'].append({
# #         "FileID":str(item["FileID"])
# #     })
# #     for clause in item['Clauses']:
# #         query['$and'].append({
# #             clause['Field']:{
# #                 clause['Operator']:clause['Value']
# #             }
# #         })
# #     shape_features = get_internal('geometryFeature',**query)[0]['_items']
# #     item['Data']=list()
# #     for feature in shape_features:
# #         item['Data'].append({
# #             "EntityID":feature['EntityID'],
# #             "GlobalId":feature['GlobalId'],
# #         })
# # # def get_source_query(data):
# # #     items=data['_items']
# # #     for item in items:
# # #         get_item_query(item)  
# # app.on_fetched_item_query+=get_item_query
# # # app.on_fetched_source_query+=get_source_query


# # def get_token_item(item):
# #     para={'emailAddress':item['trimble_email'], 'key':item['trimble_key']}
# #     headers={"Content-Type":"application/json"}
# #     r = requests.post(trimble_url+'auth',data=json.dumps(para),headers=headers)
# #     item['token']=r.json()['token']
# # def get_token(items):
# #     for item in items['_items']:
# #         get_token_item(item)
# # app.on_fetched_item_trimbleToken+=get_token_item
# # app.on_fetched_resource_trimbleToken+=get_token

# # old pairwise features
# # touching or collision
# def get_item_connected(item):
#     my_geometry = getitem_internal('geometry',**{"EntityID":item["_id"]})[0]['Geometry']
#     my_mesh=Geom(my_geometry).mesh
#     my_bound=my_mesh.bounds.reshape(1,6)[0]
#     my_tree=my_mesh.triangles_tree()
    
#     app.config['DOMAIN']['geometry']['pagination'] = False
#     geometries = get_internal('geometry',**{"FileID":item["FileID"],"EntityID":{'$ne':item["_id"]}})[0]['_items']
#     compare=list()
#     for geometry in geometries:
#         mesh=Geom(geometry['Geometry']).mesh
#         # bound=mesh.bounds.reshape(1,6)[0]
#         bound=mesh.bounds
#         bound=np.array([bound[0].dot(0.99).tolist(),bound[1].dot(1.01).tolist()]).reshape(1,6)[0]
#         potential_triangle_indices=list(my_tree.intersection(bound))
#         if len(potential_triangle_indices)>0:
#             # my_potential_points=my_mesh.triangles[potential_triangle_indices].reshape(1,len(potential_triangle_indices)*3,3)[0]
#             # checking_results=trimesh.ray.ray_mesh.contains_points(mesh,my_potential_points)
#             # if True in checking_results:
#             #     compare.append({
#             #         'EntityID':geometry['EntityID'],
#             #         'GlobalId':geometry['GlobalId'],
#             #         'Compare':1
#             #     })
#             #     continue
#             compare.append({
#                 'EntityID':geometry['EntityID'],
#                 'GlobalId':geometry['GlobalId'],
#                 'Compare':1
#             })
#         else:
#             compare.append({
#                 'EntityID':geometry['EntityID'],
#                 'GlobalId':geometry['GlobalId'],
#                 'Compare':-1
#             })
#     item['Compare']={
#         'Type':'Connect',
#         'Description':'either touching or collision',
#         'Vector':compare
#     }
#     app.config['DOMAIN']['geometry']['pagination'] = True
# app.on_fetched_item_connect+=get_item_connected

# # parallel extrusion
# threshhold_degree=5
# def get_item_parallel_extrusion(item):
#     my_axis = getitem_internal('geometryFeature',**{"Feature.Name":"ExtrudedAxis","EntityID":item["_id"]})[0]['Feature']['Value']
    
#     app.config['DOMAIN']['geometryFeature']['pagination'] = False
#     extrusions = get_internal('geometryFeature',**{"Feature.Name":"ExtrudedAxis","FileID":item["FileID"],"EntityID":{'$ne':item["_id"]}})[0]['_items']
#     compare=list()
#     for extrusion in extrusions:
#         axis=extrusion['Feature']['Value']
#         # the angle in degree
#         import math
#         absolute_angle=math.degrees(math.acos(abs(np.dot(my_axis,axis))))
#         # if the angle is lowere than 5
#         if absolute_angle<threshhold_degree:
#             compare.append({
#                 'EntityID':extrusion['EntityID'],
#                 'GlobalId':extrusion['GlobalId'],
#                 'Compare':1
#             })
#         else:
#             compare.append({
#                 'EntityID':extrusion['EntityID'],
#                 'GlobalId':extrusion['GlobalId'],
#                 'Compare':-1
#             })
#     item['Compare']={
#         'Type':'Parallel',
#         'Description':'we are in parallel',
#         'Vector':compare
#     }
#     app.config['DOMAIN']['geometryFeature']['pagination'] = True
# app.on_fetched_item_paraExtrusion+=get_item_parallel_extrusion

# # higher centroid
# def get_item_higherCentroid(item):
#     level = getitem_internal('geometryFeature',**{"Feature.Name":"OBBCentroid","EntityID":item["_id"]})[0]['Feature']['Value']['Z']
#     # to make sure we can retrieve all the documents
#     app.config['DOMAIN']['geometryFeature']['pagination'] = False
#     # file_id=str(item["FileID"])
#     file_id=item["FileID"]
#     compare={'Type':'Volume',
#         'Description':'I\'m higher than them',
#         'Vector':[]
#     }
#     query_greater={"$and": [
#         {"FileID":file_id},
#         {"Feature.Name":"OBBCentroid"},{"EntityID":{'$ne':item["_id"]}},
#         {"Feature.Value.Z":{"$gt":level}}]}
#     greater_entities=get_internal('geometryFeature',**query_greater)[0]['_items']
#     for entity in greater_entities:
#         compare['Vector'].append({
#             'EntityID':entity['EntityID'],
#             'GlobalId':entity['GlobalId'],
#             'Compare':-1
#         })
#     query_smaller={"$and": [
#         {"FileID":file_id},
#         {"Feature.Name":"OBBCentroid"},{"EntityID":{'$ne':item["_id"]}},
#         {"Feature.Value.Z":{"$lte":level}}]}
#     smaller_entities=get_internal('geometryFeature',**query_smaller)[0]['_items']
#     for entity in smaller_entities:
#         compare['Vector'].append({
#             'EntityID':entity['EntityID'],
#             'GlobalId':entity['GlobalId'],
#             'Compare':1
#         })
#     if len(compare['Vector'])>0:
#         item['Compare']=compare
#     app.config['DOMAIN']['geometryFeature']['pagination'] = True
# app.on_fetched_item_higherCentroid+=get_item_higherCentroid

# # higher centroid
# def get_item_lowerBottom(item):
#     level = getitem_internal('geometryFeature',**{"Feature.Name":"Min","EntityID":item["_id"]})[0]['Feature']['Value']['Z']
#     # to make sure we can retrieve all the documents
#     app.config['DOMAIN']['geometryFeature']['pagination'] = False
#     # file_id=str(item["FileID"])
#     file_id=item["FileID"]
#     compare={'Type':'Volume',
#         'Description':'I\'m lower than them',
#         'Vector':[]
#     }
#     query_greater={"$and": [
#         {"FileID":file_id},
#         {"Feature.Name":"Min"},{"EntityID":{'$ne':item["_id"]}},
#         {"Feature.Value.Z":{"$gt":level}}]}
#     greater_entities=get_internal('geometryFeature',**query_greater)[0]['_items']
#     for entity in greater_entities:
#         compare['Vector'].append({
#             'EntityID':entity['EntityID'],
#             'GlobalId':entity['GlobalId'],
#             'Compare':1
#         })
#     query_smaller={"$and": [
#         {"FileID":file_id},
#         {"Feature.Name":"Min"},{"EntityID":{'$ne':item["_id"]}},
#         {"Feature.Value.Z":{"$lte":level}}]}
#     smaller_entities=get_internal('geometryFeature',**query_smaller)[0]['_items']
#     for entity in smaller_entities:
#         compare['Vector'].append({
#             'EntityID':entity['EntityID'],
#             'GlobalId':entity['GlobalId'],
#             'Compare':-1
#         })
#     if len(compare['Vector'])>0:
#         item['Compare']=compare
#     app.config['DOMAIN']['geometryFeature']['pagination'] = True
# app.on_fetched_item_lowerBottom+=get_item_lowerBottom

# # longger extrusion
# def get_item_longgerExtrusion(item):
#     extrusion = getitem_internal('geometryFeature',**{"Feature.Name":"ExtrusionLength","EntityID":item["_id"]})[0]['Feature']['Value']
#     # to make sure we can retrieve all the documents
#     app.config['DOMAIN']['geometryFeature']['pagination'] = False
#     # file_id=str(item["FileID"])
#     file_id=item["FileID"]
#     compare={'Type':'Volume',
#         'Description':'I\'m longger than them',
#         'Vector':[]
#     }
#     query_greater={"$and": [
#         {"FileID":file_id},
#         {"Feature.Name":"ExtrusionLength"},{"EntityID":{'$ne':item["_id"]}},
#         {"Feature.Value":{"$gt":extrusion}}]}
#     greater_entities=get_internal('geometryFeature',**query_greater)[0]['_items']
#     for entity in greater_entities:
#         compare['Vector'].append({
#             'EntityID':entity['EntityID'],
#             'GlobalId':entity['GlobalId'],
#             'Compare':-1
#         })
#     query_smaller={"$and": [
#         {"FileID":file_id},
#         {"Feature.Name":"ExtrusionLength"},{"EntityID":{'$ne':item["_id"]}},
#         {"Feature.Value":{"$lte":extrusion}}]}
#     smaller_entities=get_internal('geometryFeature',**query_smaller)[0]['_items']
#     for entity in smaller_entities:
#         compare['Vector'].append({
#             'EntityID':entity['EntityID'],
#             'GlobalId':entity['GlobalId'],
#             'Compare':1
#         })
#     if len(compare['Vector'])>0:
#         item['Compare']=compare
#     app.config['DOMAIN']['geometryFeature']['pagination'] = True
# app.on_fetched_item_longgerExtrusion+=get_item_longgerExtrusion

# # parallel extrusion
# threshhold_degree=5
# bridge_longitudinal=[1,0,0]
# def get_item_parallelBridge(item):
#     my_feature = getitem_internal('geometryFeature',**{"Feature.Name":"ExtrudedAxis","EntityID":item["_id"]})[0]
#     my_axis=my_feature['Feature']['Value']
#     import math
#     absolute_angle=math.degrees(math.acos(abs(np.dot(my_axis,bridge_longitudinal))))
#         # if the angle is lowere than 5
#     if absolute_angle<threshhold_degree:
#         compare=1
#     else:
#         compare=-1
#     item['Compare']={
#         'Type':'Parallel',
#         'Description':'we are in parallel',
#         'Vector':[{
#             'EntityID':item['_id'],
#             'GlobalId':my_feature['GlobalId'],
#             'Compare':compare
#         }]
#     }
# app.on_fetched_item_parallelBridge+=get_item_parallelBridge

# # compare volume
# def get_item_volumeBigger(item):
#     volume = getitem_internal('geometryFeature',**{"Feature.Name":"Volume","EntityID":item["_id"]})[0]['Feature']['Value']
#     # to make sure we can retrieve all the documents
#     app.config['DOMAIN']['geometryFeature']['pagination'] = False
#     # file_id=str(item["FileID"])
#     file_id=item["FileID"]
#     compare={'Type':'Volume',
#         'Description':'My Volume is greater than theirs',
#         'Vector':[]
#     }
#     query_greater={"$and": [
#         {"FileID":file_id},
#         {"Feature.Name":"Volume"},
#         {"Feature.Value":{"$gt":volume}},{"EntityID":{'$ne':item["_id"]}}]}
#     greater_entities=get_internal('geometryFeature',**query_greater)[0]['_items']
#     for entity in greater_entities:
#         compare['Vector'].append({
#             'EntityID':entity['EntityID'],
#             'GlobalId':entity['GlobalId'],
#             'Compare':-1
#         })
#     query_smaller={"$and": [
#         {"FileID":file_id},
#         {"Feature.Name":"Volume"},
#         {"Feature.Value":{"$lte":volume}},{"EntityID":{'$ne':item["_id"]}}]}
#     smaller_entities=get_internal('geometryFeature',**query_smaller)[0]['_items']
#     for entity in smaller_entities:
#         compare['Vector'].append({
#             'EntityID':entity['EntityID'],
#             'GlobalId':entity['GlobalId'],
#             'Compare':1
#         })
#     if len(compare['Vector'])>0:
#         item['Compare']=compare
#     app.config['DOMAIN']['geometryFeature']['pagination'] = True
# app.on_fetched_item_volumeBigger+=get_item_volumeBigger

# # complete above
# def get_item_completeAbove(item):
#     lowest_level = getitem_internal('geometryFeature',**{"Feature.Name":"Min","EntityID":item["_id"]})[0]['Feature']['Value']['Z']
#     # to make sure we can retrieve all the documents
#     app.config['DOMAIN']['geometryFeature']['pagination'] = False
#     features = get_internal('geometryFeature',**{"Feature.Name":"Max","FileID":item["FileID"],"EntityID":{'$ne':item["_id"]}})[0]['_items']
#     compare=list()
#     for feature in features:
#         max_level=feature['Feature']['Value']['Z']
#         if lowest_level>max_level or np.isclose(lowest_level,max_level,atol=1e-1):
#             compare.append({
#                 'EntityID':feature['EntityID'],
#                 'GlobalId':feature['GlobalId'],
#                 'Compare':1
#             })
#         else:
#             compare.append({
#                 'EntityID':feature['EntityID'],
#                 'GlobalId':feature['GlobalId'],
#                 'Compare':-1
#             })
#     item['Compare']={
#         'Type':'Completely above',
#         'Description':'I\'m completely above them',
#         'Vector':compare
#     }
#     app.config['DOMAIN']['geometryFeature']['pagination'] = True
# app.on_fetched_item_completeAbove+=get_item_completeAbove

# # closer to bridge's Longitudinal axis
# bridge_longitudinal_axis='X'
# bridge_transverse_axis='Y'
# def bridgeCentroid(fileID):
#     mins=get_internal('geometryFeature',**{"Feature.Name":"Min","FileID":fileID})[0]['_items']
#     model_min=dict()
#     for min in mins:
#         if not model_min:
#             model_min['X']=min['Feature']['Value']['X']
#             model_min['Y']=min['Feature']['Value']['Y']
#             model_min['Z']=min['Feature']['Value']['Z']
#             continue
#         if model_min['X']>min['Feature']['Value']['X']:
#             model_min['X']=min['Feature']['Value']['X']
#         if model_min['Y']>min['Feature']['Value']['Y']:
#             model_min['Y']=min['Feature']['Value']['Y']
#         if model_min['Z']>min['Feature']['Value']['Z']:
#             model_min['Z']=min['Feature']['Value']['Z']
#     maxs=get_internal('geometryFeature',**{"Feature.Name":"Max","FileID":fileID})[0]['_items']
#     model_max=dict()
#     for max in maxs:
#         if not model_max:
#             model_max['X']=max['Feature']['Value']['X']
#             model_max['Y']=max['Feature']['Value']['Y']
#             model_max['Z']=max['Feature']['Value']['Z']
#             continue
#         if model_max['X']<max['Feature']['Value']['X']:
#             model_max['X']=max['Feature']['Value']['X']
#         if model_max['Y']<max['Feature']['Value']['Y']:
#             model_max['Y']=max['Feature']['Value']['Y']
#         if model_max['Z']<max['Feature']['Value']['Z']:
#             model_max['Z']=max['Feature']['Value']['Z']
#     return {
#         'X':(model_max['X']+model_min['X'])/2,
#         'Y':(model_max['Y']+model_min['Y'])/2,
#         'Z':(model_max['Z']+model_min['Z'])/2,
#     }
    
#     # geometries=get_internal('geometry',**{"FileID":fileID})[0]['_items']
#     # data=dict()
#     # v_len=0
#     # for geometry in geometries:
#     #     v_array=geometry['Geometry']['Vertices']
#     #     f_array=geometry['Geometry']['Faces']
#     #     np.add(f_array,v_len)
#     #     n_array=geometry['Geometry']['Normals']
#     #     if not data:
#     #         data['Vertices']=v_array
#     #         data['Faces']=f_array
#     #         data['Normals']=n_array
#     #     else:
#     #         data['Vertices']=np.concatenate((data['Vertices'],v_array),axis=0).tolist()
#     #         data['Faces']=np.concatenate((data['Faces'],f_array),axis=0).tolist()
#     #         data['Normals']=np.concatenate((data['Normals'],n_array),axis=0).tolist()
#     #     v_len=len(v_array)
#     # # ceontroid=np.mean(data['Vertices'],axis=0).tolist()
#     # model=Geom(data)
#     # ceontroid=np.mean(model.mesh.bounds,axis=0).tolist()
#     # # ceontroid=model.mesh.centroid.tolist()
#     # return {
#     #     'X':ceontroid[0],
#     #     'Y':ceontroid[1],
#     #     'Z':ceontroid[2]
#     # }
    
    
# def get_item_closerTransverseCoordinate(item):
#     my_t_c = getitem_internal('geometryFeature',**{"Feature.Name":"Centroid","EntityID":item["_id"]})[0]['Feature']['Value'][bridge_transverse_axis]
#     bridge_centroid=bridgeCentroid(item['FileID'])
#     b_t_c=bridge_centroid[bridge_transverse_axis]
#     # to make sure we can retrieve all the documents
#     app.config['DOMAIN']['geometryFeature']['pagination'] = False
#     features = get_internal('geometryFeature',**{"Feature.Name":"Centroid","FileID":item["FileID"],"EntityID":{'$ne':item["_id"]}})[0]['_items']
#     compare=list()
#     for feature in features:
#         t_c=feature['Feature']['Value'][bridge_transverse_axis]
#         if abs(my_t_c-b_t_c)<=abs(t_c-b_t_c):
#             compare.append({
#                 'EntityID':feature['EntityID'],
#                 'GlobalId':feature['GlobalId'],
#                 'Compare':1
#             })
#         else:
#             compare.append({
#                 'EntityID':feature['EntityID'],
#                 'GlobalId':feature['GlobalId'],
#                 'Compare':-1
#             })
#     item['Compare']={
#         'Type':'Completely above',
#         'Description':'I\'m closer to bridge\'s Longitudinal axis',
#         'Vector':compare
#     }
#     app.config['DOMAIN']['geometryFeature']['pagination'] = True
# def get_item_closerLongitudinalCoordinate(item):
#     my_centroid = getitem_internal('geometryFeature',**{"Feature.Name":"Centroid","EntityID":item["_id"]})[0]['Feature']['Value']
#     my_t_c=my_centroid[bridge_longitudinal_axis]
#     bridge_centroid=bridgeCentroid(item['FileID'])
#     b_t_c=bridge_centroid[bridge_longitudinal_axis]
#     # to make sure we can retrieve all the documents
#     app.config['DOMAIN']['geometryFeature']['pagination'] = False
#     features = get_internal('geometryFeature',**{"Feature.Name":"Centroid","FileID":item["FileID"],"EntityID":{'$ne':item["_id"]}})[0]['_items']
#     compare=list()
#     for feature in features:
#         t_c=feature['Feature']['Value'][bridge_longitudinal_axis]
#         if abs(my_t_c-b_t_c)<=abs(t_c-b_t_c):
#             compare.append({
#                 'EntityID':feature['EntityID'],
#                 'GlobalId':feature['GlobalId'],
#                 'Compare':1
#             })
#         else:
#             compare.append({
#                 'EntityID':feature['EntityID'],
#                 'GlobalId':feature['GlobalId'],
#                 'Compare':-1
#             })
#     item['Compare']={
#         'Type':'Completely above',
#         'Description':'I\'m closer to bridge\'s Longitudinal axis',
#         'Vector':compare
#     }
#     app.config['DOMAIN']['geometryFeature']['pagination'] = True
# app.on_fetched_item_closerTran+=get_item_closerLongitudinalCoordinate
# app.on_fetched_item_closerLongi+=get_item_closerTransverseCoordinate

# # parallel bridge's transverse direction
# threshhold_degree=5
# bridge_transverse=[0,1,0]
# def get_item_paraBriTrans(item):
#     my_feature = getitem_internal('geometryFeature',**{"Feature.Name":"ExtrudedAxis","EntityID":item["_id"]})[0]
#     my_axis=my_feature['Feature']['Value']
#     import math
#     absolute_angle=math.degrees(math.acos(abs(np.dot(my_axis,bridge_transverse))))
#         # if the angle is lowere than 5
#     if absolute_angle<threshhold_degree:
#         compare=1
#     else:
#         compare=-1
#     item['Compare']={
#         'Type':'Parallel',
#         'Description':'we are in parallel',
#         'Vector':[{
#             'EntityID':item['_id'],
#             'GlobalId':my_feature['GlobalId'],
#             'Compare':compare
#         }]
#     }
# app.on_fetched_item_paraBriTrans+=get_item_paraBriTrans

# # parallel z
# threshhold_degree=5
# Z=[0,0,1]
# def get_item_Vertical(item):
#     my_feature = getitem_internal('geometryFeature',**{"Feature.Name":"ExtrudedAxis","EntityID":item["_id"]})[0]
#     my_axis=my_feature['Feature']['Value']
#     import math
#     absolute_angle=math.degrees(math.acos(abs(np.dot(my_axis,Z))))
#         # if the angle is lowere than 5
#     if absolute_angle<threshhold_degree:
#         compare=1
#     else:
#         compare=-1
#     item['Compare']={
#         'Type':'Parallel',
#         'Description':'I\'m vertical',
#         'Vector':[{
#             'EntityID':item['_id'],
#             'GlobalId':my_feature['GlobalId'],
#             'Compare':compare
#         }]
#     }
# app.on_fetched_item_Vertical+=get_item_Vertical

# # overlap in z [0,0,1]
# def get_item_overlapZ(item):
#     my_min = getitem_internal('geometryFeature',**{"Feature.Name":"Min","EntityID":item["_id"]})[0]['Feature']['Value']['Z']
#     my_max = getitem_internal('geometryFeature',**{"Feature.Name":"Max","EntityID":item["_id"]})[0]['Feature']['Value']['Z']
#     app.config['DOMAIN']['geometry']['pagination'] = False
#     geometries = get_internal('geometry',**{"FileID":item["FileID"]})[0]['_items']
#     compare=list()
#     for geometry in geometries:
#         min = getitem_internal('geometryFeature',**{"Feature.Name":"Min","EntityID":geometry["EntityID"]})[0]['Feature']['Value']['Z']
#         max = getitem_internal('geometryFeature',**{"Feature.Name":"Max","EntityID":geometry["EntityID"]})[0]['Feature']['Value']['Z']
#         if my_min<max and my_max>min:
#             compare.append({
#                 'EntityID':geometry['EntityID'],
#                 'GlobalId':geometry['GlobalId'],
#                 'Compare':1
#             })
#         else:
#             compare.append({
#                 'EntityID':geometry['EntityID'],
#                 'GlobalId':geometry['GlobalId'],
#                 'Compare':-1
#             })
#     item['Compare']={
#         'Type':'Completely above',
#         'Description':'I overlap with them in z',
#         'Vector':compare
#     }
#     app.config['DOMAIN']['geometry']['pagination'] = True
# app.on_fetched_item_overlapZ+=get_item_overlapZ

# # convex
# def get_item_convex(item):
#     my_feature = getitem_internal('geometryFeature',**{"Feature.Name":"IsConvex","EntityID":item["_id"]})[0]
#     convex=my_feature['Feature']['Value']
#     if convex:
#         compare=1
#     else:
#         compare=-1
#     item['Compare']={
#         'Type':'Convex',
#         'Description':'I\'m convex',
#         'Vector':[{
#             'EntityID':item['_id'],
#             'GlobalId':my_feature['GlobalId'],
#             'Compare':compare
#         }]
#     }
# app.on_fetched_item_convex+=get_item_convex

if __name__ == '__main__':
    # app.run()
    # particularly for cloud 9 use
    app.run(host=os.environ['IP'],port=int(os.environ['PORT']),debug=True)