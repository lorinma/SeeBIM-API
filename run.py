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
# add geometry and related features
def add_geometry(items):
    for item in items:
        entity = getitem_internal('entity',**{"$and": [{"FileID":str(item["FileID"])},{"Attribute": {"$elemMatch":{"Value": str(item["GlobalId"]),"Name": "GlobalId"}}}]})[0]
        item['EntityID']=entity["_id"]
        # add features
        mesh=Geom(item['Geometry'])
        payload=list()
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
        post_internal('geometryFeature',payload,skip_validation=True)
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
def get_source_with_shape(data):
    items=data['_items']
    for item in items:
        get_item_with_property(item)  
app.on_fetched_item_entityGeomFeature+=get_item_with_shape
app.on_fetched_source_entityGeomFeature+=get_source_with_shape

# # only return documents that have property sets, 
# # however, ifcobject will start having properties, so potentially there're many
# # in addition, an ifcproduct may not have property, then it is unexpectedly removed from the list
# def pre_get_entity_geom_feature(request, lookup):
#     lookup["PropertySets"] = {'$exists': True}
# app.on_pre_GET_entityGeomFeature += pre_get_entity_geom_feature

###########################################
# pairwise features

# compare volume
def get_item_volumeBigger(item):
    volume = getitem_internal('geometryFeature',**{"Feature.Name":"Volume","EntityID":item["_id"]})[0]['Feature']['Value']
    # to make sure we can retrieve all the documents
    app.config['DOMAIN']['geometryFeature']['pagination'] = False
    # file_id=str(item["FileID"])
    file_id=item["FileID"]
    compare={'Type':'Volume',
        'Description':'My Volume is greater than theirs',
        'Vector':[]
    }
    query_greater={"$and": [
        {"FileID":file_id},
        {"Feature.Name":"Volume"},
        {"Feature.Value":{"$gt":volume}},{"EntityID":{'$ne':item["_id"]}}]}
    greater_entities=get_internal('geometryFeature',**query_greater)[0]['_items']
    for entity in greater_entities:
        compare['Vector'].append({
            'EntityID':entity['EntityID'],
            'GlobalId':entity['GlobalId'],
            'Compare':-1
        })
    query_smaller={"$and": [
        {"FileID":file_id},
        {"Feature.Name":"Volume"},
        {"Feature.Value":{"$lte":volume}},{"EntityID":{'$ne':item["_id"]}}]}
    smaller_entities=get_internal('geometryFeature',**query_smaller)[0]['_items']
    for entity in smaller_entities:
        compare['Vector'].append({
            'EntityID':entity['EntityID'],
            'GlobalId':entity['GlobalId'],
            'Compare':1
        })
    if len(compare['Vector'])>0:
        item['Compare']=compare
    app.config['DOMAIN']['geometryFeature']['pagination'] = True
app.on_fetched_item_volumeBigger+=get_item_volumeBigger

# parallel extrusion
threshhold_degree=5
def get_item_parallel_extrusion(item):
    my_axis = getitem_internal('geometryFeature',**{"Feature.Name":"ExtrudedAxis","EntityID":item["_id"]})[0]['Feature']['Value']
    
    app.config['DOMAIN']['geometryFeature']['pagination'] = False
    extrusions = get_internal('geometryFeature',**{"Feature.Name":"ExtrudedAxis","FileID":item["FileID"],"EntityID":{'$ne':item["_id"]}})[0]['_items']
    compare=list()
    for extrusion in extrusions:
        axis=extrusion['Feature']['Value']
        # the angle in degree
        import math
        absolute_angle=math.degrees(math.acos(abs(np.dot(my_axis,axis))))
        print(absolute_angle)
        # if the angle is lowere than 5
        if absolute_angle<threshhold_degree:
            compare.append({
                'EntityID':extrusion['EntityID'],
                'GlobalId':extrusion['GlobalId'],
                'Compare':1
            })
        else:
            compare.append({
                'EntityID':extrusion['EntityID'],
                'GlobalId':extrusion['GlobalId'],
                'Compare':-1
            })
    item['Compare']={
        'Type':'Parallel',
        'Description':'we are in parallel',
        'Vector':compare
    }
    app.config['DOMAIN']['geometryFeature']['pagination'] = True
app.on_fetched_item_paraExtrusion+=get_item_parallel_extrusion

# longger extrusion
def get_item_longgerExtrusion(item):
    extrusion = getitem_internal('geometryFeature',**{"Feature.Name":"ExtrusionLength","EntityID":item["_id"]})[0]['Feature']['Value']
    # to make sure we can retrieve all the documents
    app.config['DOMAIN']['geometryFeature']['pagination'] = False
    # file_id=str(item["FileID"])
    file_id=item["FileID"]
    compare={'Type':'Volume',
        'Description':'I\'m longger than them',
        'Vector':[]
    }
    query_greater={"$and": [
        {"FileID":file_id},
        {"Feature.Name":"ExtrusionLength"},{"EntityID":{'$ne':item["_id"]}},
        {"Feature.Value":{"$gt":extrusion}}]}
    greater_entities=get_internal('geometryFeature',**query_greater)[0]['_items']
    for entity in greater_entities:
        compare['Vector'].append({
            'EntityID':entity['EntityID'],
            'GlobalId':entity['GlobalId'],
            'Compare':-1
        })
    query_smaller={"$and": [
        {"FileID":file_id},
        {"Feature.Name":"ExtrusionLength"},{"EntityID":{'$ne':item["_id"]}},
        {"Feature.Value":{"$lte":extrusion}}]}
    smaller_entities=get_internal('geometryFeature',**query_smaller)[0]['_items']
    for entity in smaller_entities:
        compare['Vector'].append({
            'EntityID':entity['EntityID'],
            'GlobalId':entity['GlobalId'],
            'Compare':1
        })
    if len(compare['Vector'])>0:
        item['Compare']=compare
    print(len(compare['Vector']))
    app.config['DOMAIN']['geometryFeature']['pagination'] = True
app.on_fetched_item_longgerExtrusion+=get_item_longgerExtrusion

# higher centroid
def get_item_higherCentroid(item):
    level = getitem_internal('geometryFeature',**{"Feature.Name":"OBBCentroid","EntityID":item["_id"]})[0]['Feature']['Value']['Z']
    # to make sure we can retrieve all the documents
    app.config['DOMAIN']['geometryFeature']['pagination'] = False
    # file_id=str(item["FileID"])
    file_id=item["FileID"]
    compare={'Type':'Volume',
        'Description':'I\'m higher than them',
        'Vector':[]
    }
    query_greater={"$and": [
        {"FileID":file_id},
        {"Feature.Name":"OBBCentroid"},{"EntityID":{'$ne':item["_id"]}},
        {"Feature.Value.Z":{"$gt":level}}]}
    greater_entities=get_internal('geometryFeature',**query_greater)[0]['_items']
    for entity in greater_entities:
        compare['Vector'].append({
            'EntityID':entity['EntityID'],
            'GlobalId':entity['GlobalId'],
            'Compare':-1
        })
    query_smaller={"$and": [
        {"FileID":file_id},
        {"Feature.Name":"OBBCentroid"},{"EntityID":{'$ne':item["_id"]}},
        {"Feature.Value.Z":{"$lte":level}}]}
    smaller_entities=get_internal('geometryFeature',**query_smaller)[0]['_items']
    for entity in smaller_entities:
        compare['Vector'].append({
            'EntityID':entity['EntityID'],
            'GlobalId':entity['GlobalId'],
            'Compare':1
        })
    if len(compare['Vector'])>0:
        item['Compare']=compare
    app.config['DOMAIN']['geometryFeature']['pagination'] = True
app.on_fetched_item_higherCentroid+=get_item_higherCentroid

# complete above
def get_item_completeAbove(item):
    lowest_level = getitem_internal('geometryFeature',**{"Feature.Name":"Min","EntityID":item["_id"]})[0]['Feature']['Value']['Z']
    # to make sure we can retrieve all the documents
    app.config['DOMAIN']['geometryFeature']['pagination'] = False
    # file_id=str(item["FileID"])
    file_id=item["FileID"]
    compare={'Type':'Volume',
        'Description':'I\'m higher than them',
        'Vector':[]
    }
    query_greater={"$and": [
        {"FileID":file_id},
        {"Feature.Name":"Max"},{"EntityID":{'$ne':item["_id"]}},
        {"Feature.Value.Z":{"$gt":lowest_level}}]}
    greater_entities=get_internal('geometryFeature',**query_greater)[0]['_items']
    for entity in greater_entities:
        compare['Vector'].append({
            'EntityID':entity['EntityID'],
            'GlobalId':entity['GlobalId'],
            'Compare':-1
        })
    query_smaller={"$and": [
        {"FileID":file_id},
        {"Feature.Name":"Max"},{"EntityID":{'$ne':item["_id"]}},
        {"Feature.Value.Z":{"$lte":lowest_level}}]}
    smaller_entities=get_internal('geometryFeature',**query_smaller)[0]['_items']
    for entity in smaller_entities:
        compare['Vector'].append({
            'EntityID':entity['EntityID'],
            'GlobalId':entity['GlobalId'],
            'Compare':1
        })
    if len(compare['Vector'])>0:
        item['Compare']=compare
    app.config['DOMAIN']['geometryFeature']['pagination'] = True
app.on_fetched_item_completeAbove+=get_item_completeAbove

# touching or collision
def get_item_connect(item):
    my_geometry = getitem_internal('geometry',**{"EntityID":item["_id"]})[0]['Geometry']
    my_mesh=Geom(my_geometry).mesh
    my_tree=my_mesh.triangles_tree()
    
    app.config['DOMAIN']['geometryFeature']['pagination'] = False
    geometries = get_internal('geometry',**{"FileID":item["FileID"],"EntityID":{'$ne':item["_id"]}})[0]['_items']
    print(len(geometries))
    compare=list()
    for geometry in geometries:
        mesh=Geom(geometry['Geometry']).mesh
        bound=mesh.bounds.reshape(1,6)[0]
        potential_triangle_indices=list(my_tree.intersection(bound))
        if len(potential_triangle_indices)==0:
            continue
        my_potential_points=my_mesh.triangles[potential_triangle_indices].reshape(1,len(potential_triangle_indices)*3,3)[0]
        checking_results=trimesh.ray.ray_mesh.contains_points(mesh,my_potential_points)
        if True in checking_results:
            compare.append({
                'EntityID':geometry['EntityID'],
                'GlobalId':geometry['GlobalId'],
                'Compare':1
            })    
        else:
            compare.append({
                'EntityID':geometry['EntityID'],
                'GlobalId':geometry['GlobalId'],
                'Compare':-1
            })
    item['Compare']={
        'Type':'Connect',
        'Description':'either touching or collision',
        'Vector':compare
    }
    app.config['DOMAIN']['geometryFeature']['pagination'] = True
app.on_fetched_item_connect+=get_item_connect


###########################################
# deletion

# delete entity 
# def delete_entity(item):
#     while 1:
#         geometries=get_internal('geometry',**{'EntityID': item["_id"]})[0]["_items"]
#         if len(geometries)<1:
#             break
#         for geometry in geometries:
#             deleteitem_internal('geometry',**{"_id":geometry['_id']})
# def delete_all_entity():
#     items = get_internal('entity')[0]['_items']
#     for item in items:
#         delete_entity(item)
# app.on_delete_item_entity+=delete_entity
# app.on_delete_resource_entity+=delete_all_entity


# below are old staff
###########################################

def get_trimble_file(item):
    item['trimble_token']=get_trimble_token()
def delete_file(item):
    while 1:
        entities=get_internal('entity',**{'FileID': item["_id"]})[0]["_items"]
        if len(entities)<1:
            break
        for entity in entities:
            deleteitem_internal('entity',**{"_id":entity['_id']})
def delete_all_file():
    files = get_internal('file')[0]['_items']
    for file in files:
        delete_file(file)

app.on_fetched_item_fileTrimble+=get_trimble_file
# don't want the web interface to delete too slow
# app.on_delete_item_file+=delete_file
app.on_delete_resource_file+=delete_all_file


# interaction with entity attributes
def get_attribute_value(attributes,attribute_name):
    for attribute in attributes:
        if attribute['Name']==attribute_name:
            return attribute['Value']
    print("No such attribute")
    return None
def set_attribute_value(attributes,attribute_name,value):
    for attribute in attributes:
        if attribute['Name']==attribute_name:
            attribute['Value']=value
    return attributes
    
# entity property set interaction
def get_item_property_set(item):
    properties=get_attribute_value(item['Attribute'],'HasProperties')
    if properties is None:
        return
    # if the attribute like HasProperties only has 1 node, then it is a str instead of list
    if isinstance(properties,str):
        properties=[properties]
    properties_data=list()
    for property in properties:
        try:
            property_data=getitem_internal('entitySimple',**{"_id":property})
            properties_data.append(property_data[0])
        except:
            print("No such property")
    if len(properties_data)>0:
        item['Properties']=properties_data
def get_property_set(data):
    items=data['_items']
    for item in items:
        get_item_property_set(item)        
app.on_fetched_item_entityPropertySet+=get_item_property_set  
app.on_fetched_resource_entityPropertySet+=get_property_set

# reldefined
def get_item_rel_property_set(item):
    # do we really need try here?
    try:
        property_set_id=get_attribute_value(item['Attribute'],'RelatingPropertyDefinition')
        if property_set_id is not None:
            p_set=getitem_internal('entityPropertySet',**{"_id":ObjectId(property_set_id)})[0]
            item['PropertySet']=p_set
    except:
        print("no property set linked in this relation")
def get_rel_property_set(data):
    items=data['_items']
    for item in items:
        get_item_rel_property_set(item)  
app.on_fetched_item_entityRelProperties+=get_item_rel_property_set
app.on_fetched_resource_entityRelProperties+=get_rel_property_set

# entity with property set interaction
# you can only query specific entity item
def get_item_with_property(item):
    print(item['_id'])
    rels = get_internal('entityRelProperties',**{"Attribute": {"$elemMatch":{"Value": str(item['_id']),"Name": "RelatedObjects"}}})[0]['_items']
    if len(rels)>0:
        item['PropertyDefinition']=rels
    shape_feature = getitem_internal('geometryWithFeature',**{"EntityID":item["_id"]})[0]
    item['Geometry']=shape_feature['Geometry']
    features=list()
    for feature in shape_feature['Features']:
        features.append(feature)
    item['Features']=features
def get_resource_with_property(data):
    items=data['_items']
    for item in items:
        get_item_with_property(item)  
app.on_fetched_item_entityWithProperty+=get_item_with_property
app.on_fetched_resource_entityWithProperty+=get_resource_with_property

# shape and feature
def get_item_shape_with_feature(item):
    features = get_internal('geometryFeature',**{"GeometryID":item["_id"]})[0]['_items']
    if len(features)>0:
        item['Features']=list()
        for feature in features:
            item['Features'].append(feature['Feature'])
    else:
        item['Features']=list()
        mesh=Geom(item['Geometry'])
        payload=list()
        obb_features=mesh.getOBB()
        shape_features=mesh.getMeshFeature()
        data=dict()
        for obb_feature in obb_features:
            payload.append({
                'FileID':str(item['FileID']),
                'GlobalId':str(item['GlobalId']),
                'EntityID':str(item['EntityID']),
                'GeometryID':str(item['_id']),
                'Feature':obb_feature
            })
            item['Features'].append(obb_feature)
        for shape_feature in shape_features:
            payload.append({
                'FileID':str(item['FileID']),
                'GlobalId':str(item['GlobalId']),
                'EntityID':str(item['EntityID']),
                'GeometryID':str(item['_id']),
                'Feature':shape_feature
            })
            item['Features'].append(shape_feature)
        post_internal('geometryFeature',payload,skip_validation=True)
def get_resource_shape_with_feature(data):
    items=data['_items']
    for item in items:
        get_item_shape_with_feature(item)  
def delete_geometry(item):
    while 1:
        features=get_internal('geometryFeature',**{'GeometryID': item["_id"]})[0]["_items"]
        if len(features)<1:
            break
        for feature in features:
            deleteitem_internal('geometryFeature',**{"_id":feature['_id']})


def delete_all_geometry():
    items = get_internal('geometry')[0]['_items']
    for item in items:
        delete_geometry(item)
app.on_fetched_item_geometryWithFeature+=get_item_shape_with_feature
app.on_fetched_resource_geometryWithFeature+=get_resource_shape_with_feature

app.on_delete_item_geometry+=delete_geometry
app.on_delete_resource_geometry+=delete_all_geometry


def getFeature(item,feature_name):
    features=item['Features']
    for feature in features:
        if feature['Name']==feature_name:
            return feature['Value']
    return None
    
# Bug: cannot fetch these extra items, even not print 
# def get_item_feature_entity(item):
#     print("ol1")
#     entity = getitem_internal('entityWithProperty',**{"_id":item["EntityID"]})[0]
#     print(entity)
#     item['Entity']=entity
# def get_source_feature_entity(data):
#     print("data")
#     items=data['_items']
#     print("ol")
#     for item in items:
#         get_item_feature_entity(item)  
# app.on_fetched_item_geometryFeature+=get_item_feature_entity
# app.on_fetched_source_geometryFeature+=get_source_feature_entity

# query
def get_item_query(item):
    query=dict()
    query["$and"]=list()
    query['$and'].append({
        "FileID":str(item["FileID"])
    })
    for clause in item['Clauses']:
        query['$and'].append({
            clause['Field']:{
                clause['Operator']:clause['Value']
            }
        })
    shape_features = get_internal('geometryFeature',**query)[0]['_items']
    item['Data']=list()
    for feature in shape_features:
        item['Data'].append({
            "EntityID":feature['EntityID'],
            "GlobalId":feature['GlobalId'],
        })
# def get_source_query(data):
#     items=data['_items']
#     for item in items:
#         get_item_query(item)  
app.on_fetched_item_query+=get_item_query
# app.on_fetched_source_query+=get_source_query


def get_user_by_firebase_uid(firebase_uid):
    return getitem_internal('user',**{'firebase_uid': firebase_uid})[0]
def get_token_item(item):
    para={'emailAddress':item['trimble_email'], 'key':item['trimble_key']}
    headers={"Content-Type":"application/json"}
    r = requests.post(trimble_url+'auth',data=json.dumps(para),headers=headers)
    item['token']=r.json()['token']
def get_token(items):
    for item in items['_items']:
        get_token_item(item)
app.on_fetched_item_trimbleToken+=get_token_item
app.on_fetched_resource_trimbleToken+=get_token



if __name__ == '__main__':
    # app.run()
    # particularly for cloud 9 use
    app.run(host=os.environ['IP'],port=int(os.environ['PORT']),debug=True)