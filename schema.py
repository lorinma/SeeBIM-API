# Author: Dr. Ling Ma
# https://il.linkedin.com/in/cvlingma

token_log_schema = {
    'TrimbleToken': {'type':'string'},
}

file_schema = {
    'UserID': {'type':'string'},
    'TrimbleVersionID': {'type':'string'},
}

feature_schema = {
    'FeatureProvider': {'type':'string'},
    'FeatureType': {'type':'string'},
    'FeatureName': {'type':'string'},
    'FeatureDescription': {'type':'string'},
    'FeatureValue': {},
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
}

feature_resource = {
    'item_title': 'ObjectFeature',
    'schema': feature_schema,
}