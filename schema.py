# Author: Dr. Ling Ma
# https://il.linkedin.com/in/cvlingma

token_log_schema = {
    'TrimbleToken': {'type':'string'},
}

file_schema = {
    'UserID': {'type':'string'},
    # post the url to this api for later downloading and processing model
    'Url': {'type':'string'},
    'TrimbleVersionID': {'type':'string'},
    'ThumbnailUrl': {'type':'string'},
    'TrimbleProjectID': {'type':'string'},
    'Entities':{
        'type': 'list',
        'schema': {
            'type':'dict',
            'schema':{
                'GlobalId': {'type':'string'},
                'IFCType': {'type':'string'},
                'Geometry': {
                    'type': 'dict',
                    'schema': {
                        'Unit':{'type':'string'},
                        'Faces': { 
                            'type': 'list',
                            'schema': {
                                'type':'list',
                                'schema':{
                                    'type': 'number'
                                }
                            }
                        },
                        'Normals': { 
                            'type': 'list',
                            'schema': {
                                'type':'list',
                                'schema':{
                                    'type': 'number'
                                }
                            }
                        },
                        'Vertices': { 
                            'type': 'list',
                            'schema': {
                                'type':'list',
                                'schema':{
                                    'type': 'number'
                                }
                            }
                        },
                        'OCEBrep': {'type': 'string'}
                    }
                },
            }
        }
    }
}

feature_schema = {
    'FeatureProvider': {'type':'string'},
    'FeatureType': {'type':'string'},
    'FeatureName': {'type':'string'},
    'FeatureDescription': {'type':'string'},
    'FeatureValue': {},
    'GlobalId': {'type':'string'},
    'TrimbleVersionID': {'type':'string'},
}

token_log_resource = {
    'item_title': 'TrimbleToken',
    'schema': token_log_schema,
}

token_resoure = {
    'item_title': 'LatestToken',
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
        'ThumbnailUrl',
    ]
}

file_list_resource = {
    'item_title': 'TrimbleFile',
    'schema': file_schema,
    'datasource':{
        'source':'file',
        'projection': {
            'UserID':1,
            'ThumbnailUrl':1,
            'TrimbleVersionID':1,
        },
    }
}

# get viewer data
viewer_resource = {
    'item_title': 'TrimbleFile',
    'schema': file_schema,
    'datasource':{
        'source':'file',
        'projection': {
            'token':1,
            'TrimbleVersionID':1,
            'TrimbleProjectID':1
        },
    }
}

# change the userID
file_remove_resource = {
    'item_title': 'ChangeTrimbleFileOwner',
    'schema': file_schema,
    'datasource':{
        'source':'file',
    }
}

feature_resource = {
    'item_title': 'ObjectFeature',
    'schema': feature_schema,
}

pairwise_reversed_feature_resource = {
    'item_title': 'ObjectFeature',
    'schema': feature_schema,
    'datasource':{
        'source':'feature',
        'pagination': False
    }
    
}