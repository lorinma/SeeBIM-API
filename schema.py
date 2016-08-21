# Author: Dr. Ling Ma
# https://il.linkedin.com/in/cvlingma

token_log_schema = {
    'TrimbleToken': {'type':'string'},
}

file_schema = {
    'UserID': {'type':'string'},
    'Url': {'type':'string'},
    'TrimbleVersionID': {'type':'string'},
    'ThumbnailUrl': {'type':'string'},
}

feature_schema = {
    'FeatureProvider': {'type':'string'},
    'FeatureType': {'type':'string'},
    'FeatureName': {'type':'string'},
    'FeatureDescription': {'type':'string'},
    'FeatureValue': {},
    'GlobalId': {'type':'string'},
    'FileID': {'type':'string'},
}

token_log_resource = {
    'item_title': 'TrimbleToken',
    'schema': token_log_schema,
}

latest_token_resource = {
    'item_title': 'LatestToken',
    'schema': token_log_schema,
    'datasource':{
        'source':'log',
        'default_sort': [('_updated',-1)],
        'projection': {'TrimbleToken':1},
    }
}

file_resource = {
    'item_title': 'TrimbleFile',
    'schema': file_schema,
    'extra_response_fields':[
        'TrimbleVersionID',
        'ThumbnailUrl',
    ]
}

feature_resource = {
    'item_title': 'ObjectFeature',
    'schema': feature_schema,
}