# Author: Dr. Ling Ma
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
    'project': schema.project_resource,
    'projectRemove': schema.project_remove_resource,
    'file': schema.file_resource,
    'fileList':schema.file_list_resource,
    'viewer': schema.viewer_resource,
    'entity': schema.entity_resource,
    'feature': schema.feature_resource,
    'featureVisual': schema.pairwise_reversed_feature_resource,
    'log': schema.token_log_resource,
    'lastToken':schema.token_resoure,
    'fileRemove': schema.file_remove_resource,
}