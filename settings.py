# Author: Ling Ma
# https://il.linkedin.com/in/cvlingma

import os
import schema
from os.path import join, dirname
from dotenv import load_dotenv
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

MONGO_HOST= os.environ.get('MONGO_HOST')
MONGO_PORT= os.environ.get('MONGO_PORT')
MONGO_USERNAME= os.environ.get('MONGO_USERNAME')
MONGO_PASSWORD= os.environ.get('MONGO_PASSWORD')
MONGO_DBNAME= os.environ.get('MONGO_DBNAME')
MONGO_QUERY_BLACKLIST= ['$where']
    # # We choose to override global cache-control directives for this resource.
CACHE_CONTROL= 'max-age=10,must-revalidate'
CACHE_EXPIRES= 10
    # Enable reads (GET), inserts (POST) and DELETE for resources/collections
    # (if you omit this line, the API will default to ['GET'] and provide
    # read-only access to the endpoint).
RESOURCE_METHODS= ['GET', 'POST', 'DELETE']
    #### warning ####
    # # we'd better disable the DELETE method in production
    # 'RESOURCE_METHODS': ['GET', 'POST'],
    #### warning ####
    # Enable reads (GET), edits (PATCH), replacements (PUT) and deletes of
    # individual items  (defaults to read-only item access).
ITEM_METHODS= ['GET', 'PATCH', 'PUT', 'DELETE']
EMBEDDING= True
X_DOMAINS= '*'
X_HEADERS=['Content-Type','IF-Match']

# default 25
# PAGINATION_DEFAULT=500
               
DOMAIN= {
    'user': schema.user_resource,
    'project': schema.project_resource,
    'file': schema.file_resource,
    'fileStatus':schema.file_status_resource,
    'fileTrimble':schema.file_token_resource,
    'entity': schema.entity_resource,
    'geometry': schema.geometry_resource,
    'geometryFeature': schema.geom_feature_resource,
    'pairwiseFeature': schema.pair_feature_resource,
    'entityGeomFeature': schema.entity_withGeometryFeature_resource,
    
    # 'connect':schema.entity_connect_resource,
    # 'paraExtrusion':schema.entity_parallel_extrusion_resource,
    # 'higherCentroid':schema.entity_higher_centroid_resource,
    # 'lowerBottom':schema.entity_lower_bottom_resource,
    # 'longgerExtrusion':schema.entity_longger_extrusion_resource,
    # 'parallelBridge':schema.entity_parallel_bridge_resource,
    # 'volumeBigger':schema.entity_bigger_volume_resource,
    # 'completeAbove':schema.entity_complete_above_resource,
    # 'closerTran':schema.entity_closer_transverse_resource,
    # 'closerLongi':schema.entity_closer_longitudinal_resource,
    # 'paraBriTrans':schema.entity_parallel_bridge_transverse_resource,
    # 'Vertical':schema.entity_vertical_resource,
    # 'overlapZ':schema.entity_overlap_z_resource,
    # 'convex':schema.entity_convex_resource,
    # 'entityShapeFeatures':schema.entity_shape_features_resource,
    # 'entityPairFeatures':schema.entity_pairwise_resource,
    
    'modelShapeFeature':schema.file_model_shape_feature_resource,
    'modelPairFeature':schema.file_model_pair_feature_resource,
    'run':schema.file_run_resource,



###########################################    
# below are old staff
###########################################
    # 'entityPropertySet': schema.entity_property_set_resource,
    # 'entityRelProperties':schema.entity_relProperties_resource,
    
    # 'entityWithProperty':schema.entity_withProperty_resource,
    # 'entitySimple':schema.entity_simple_resource,
    # 'entityNoLink':schema.entity_no_link_resource,
    # 'entityGUID': schema.entity_guid_resource,
    # 'geometryWithFeature': schema.geometry_with_feature_resource,
    # 'featureSearch': schema.geom_feature_search_resource,
    
    
    # 'query': schema.query_resource,
    
    # 'trimbleToken': schema.trimbleToken_resource,
}