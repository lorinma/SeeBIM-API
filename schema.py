# Author: Ling Ma
# https://il.linkedin.com/in/cvlingma

# this is for new firebase
# user_schema = {
#     'display_name': {'type': 'string'},
#     'firebase_uid': {
#         'type': 'string',
#         # 'unique': True
#     },
#     'photo': {'type': 'string'},
    # 'trimble_email': {'type': 'string'},
    # 'trimble_key': {'type': 'string'},
# }
user_schema = {
    'firebase_uid': {'type':'string'},
    'family_name': {'type':'string'},
    'given_name': {'type':'string'},
    'gender': {'type':'string'},
    'name': {'type':'string'},
    'picture': {'type':'string'},
    'trimble_email': {'type': 'string'},
    'trimble_key': {'type': 'string'},
}
user_resource = {
    'item_title': 'User',
    'schema': user_schema,
    # # by default the standard item entry point is defined as
    # # '/people/<ObjectId>'. We leave it untouched, and we also enable an
    # # additional read-only entry point. This way consumers can also perform
    # # GET requests at '/people/<lastname>'.
    # 'additional_lookup': {
    #     'url': 'regex("[\w]+")',
    #     'field': 'firebase_uid'
    # },
    # 'extra_response_fields':[
    #     'display_name',
    #     'firebase_uid',
    #     'photo',
    #     'user_id',
    # ]
}

project_schema = {
    'name': {'type': 'string'},
    'description': {'type': 'string'},
    'firebase_uid': {
        'type': 'string',
        'data_relation': {
            'resource': 'user',
            'field': 'firebase_uid'
        }
    },
    'trimble_project_id': {'type': 'string'},
    'trimble_root_folder_id': {'type': 'string'},
    'trimble_server_region': {'type': 'string'},
    'user_id': {
        'type': 'objectid',
        'data_relation': {
            'resource': 'user',
            'field': '_id',
            'embeddable': True
        }
    }
}
project_resource = {
    'item_title': 'Project',
    'schema': project_schema,
    'extra_response_fields':[
        'firebase_uid',
        'name','description',
        'trimble_project_id',
        'trimble_root_folder_id',
        'trimble_server_region'
        ]
}

file_schema = {
    'project_id': {
        'type': 'objectid',
        'data_relation': {
            'resource': 'project',
            'field': '_id',
            'embeddable': True
        }
    },
    'source_url': {'type': 'string'},
    'name': {'type': 'string'},
    'description': {'type': 'string'},
    'user_id': {
        'type': 'objectid',
        'data_relation': {
            'resource': 'user',
            'field': '_id',
            'embeddable': True
        }
    },
    'trimble_project_id': {'type': 'string'},
    'trimble_folder_id': {'type': 'string'},
    'trimble_file_id': {'type': 'string'},
    'trimble_version_id': {'type': 'string'},
    'trimble_modifiedOn': {'type': 'datetime'},
    'trimble_createdOn': {'type': 'datetime'},
    'firebase_uid': {
        'type': 'string',
        'data_relation': {
            'resource': 'user',
            'field': 'firebase_uid'
        }
    }
}
file_resource = {
    'item_title': 'Model',
    'schema': file_schema,
    'extra_response_fields':[
        'project_id',
        'source_url',
        'trimble_folder_id',
        'trimble_project_id',
        'trimble_file_id',
        'trimble_version_id',
        'name',
        'description',
        'user_id',
        'trimble_modifiedOn',
        'trimble_createdOn',
        'firebase_uid'
    ]
}
file_status_resource={
    'datasource': {
        'source': 'file',
        'projection': {
            'firebase_uid': 1,
            'trimble_file_id': 1,
            'trimble_version_id': 1,
        },
    },
    'item_title': 'FileStatus',
    'schema': file_schema
}
file_token_resource={
    'datasource': {
        'source': 'file',
        'projection':{
            "trimble_project_id":1,
            "trimble_file_id":1,
            "trimble_version_id":1,
        }
    },
    'item_title': 'TrimbleFile',
    'schema': file_schema,
}

entity_schema = {
    'FileID': {
        'type': 'objectid',
        'data_relation': {
            'resource': 'file',
            'field': '_id',
            'embeddable': True
        },
    },
    'Line': {'type': 'integer'},
    'EntityType': {'type': 'string'},
    'Attribute': {
        'type': 'list',
        'schema': {
            'type':'dict',
            'schema':{
                'Name': {'type': 'string'},
                'Value': {},
                'Editable': {'type':'boolean'}, 
            }
        }
    },
    'UserProperty': {
        'type': 'list',
        'schema': {
            'type':'dict',
            'schema':{
                'Name': {'type': 'string'},
                'Description': {'type':'string'},
                'Children':{
                    'type': 'list',
                    'schema': {
                        'type':'dict',
                        'schema':{
                            'Name': {'type': 'string'},
                            'Description': {'type':'string'},
                            'Value': {'type':'string'},
                        }
                    }
                }
            }
        }
    },
    'Links': {
        'type': 'list',
        'schema': {
            'type':'objectid',
            'data_relation': {
                'resource': 'entity',
                'field': '_id',
                'embeddable': True
            },
        }
    },
    'PropertySets': {
        'type': 'list',
        'schema': {
            'type':'dict',
            'schema':{
                'Name': {'type': 'string'},
                'Description': {'type':'string'},
                'Properties':{
                    'type': 'list',
                    'schema': {
                        'type':'dict',
                        'schema':{
                            'Name': {'type': 'string'},
                            'Description': {'type':'string'},
                            'Value': {'type':'string'},
                        }
                    }
                }
            }
        }
    },
}
entity_resource = {
    # # 'title' tag used in item links. Defaults to the resource title minus
    # # the final, plural 's' (works fine in most cases but not for 'people')
    'item_title': 'Entity',
    'schema': entity_schema,
    'extra_response_fields':[
        'Attribute',
        'EntityType'
    ],
    # 'query_objectid_as_string':True,
}

geometry_schema = {
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
    'FileID': {
        'type': 'objectid',
        'data_relation': {
            'resource': 'file',
            'field': '_id',
            'embeddable': True
        }
    },
    'EntityID': {
        'type': 'objectid',
        'data_relation': {
            'resource': 'entity',
            'field': '_id',
            'embeddable': True
        }
    },
    'GlobalId':{'type':'string'},
}
geometry_resource = {
    'item_title': 'Geometry',
    'schema': geometry_schema,
}

geom_feature_schema = {
    'Feature': {
        'type':'dict',
        'schema':{
            'Name': {'type': 'string'},
            'Description': {'type': 'string'},
            'Value': {},
        }
    },
    'GlobalId':{'type':'string'},
    'FileID': {
        'type': 'objectid',
        'data_relation': {
            'resource': 'file',
            'field': '_id',
            'embeddable': True
        }
    },
    'EntityID': {
        'type': 'objectid',
        'data_relation': {
            'resource': 'entity',
            'field': '_id',
            'embeddable': True
        }
    },
}
geom_feature_resource = {
    'item_title': 'GeometryFeature',
    'schema': geom_feature_schema,
    'query_objectid_as_string':True,
}

entity_withGeometryFeature_resource={
    'datasource': {
        'source': 'entity',
        # 'filter': {
        #     "PropertySets":"{'$exists':1}"
        # },
    },
    'item_title': 'EntityShapeFeature',
    'schema': entity_schema
}


# either touching or collision
entity_connect_resource={
    'datasource': {
        'source': 'entity',
        'projection': {
            'FileID': 1,
            'GlobalId': 1,
        },
    },
    'item_title': 'connect',
    'schema': entity_schema
}
entity_parallel_extrusion_resource={
    'datasource': {
        'source': 'entity',
        'projection': {
            'FileID': 1,
            'GlobalId': 1,
        },
    },
    'item_title': 'paraExtrusion',
    'schema': entity_schema
}
entity_higher_centroid_resource={
    'datasource': {
        'source': 'entity',
        'projection': {
            'FileID': 1,
            'GlobalId': 1,
        },
    },
    'item_title': 'higherCentroid',
    'schema': entity_schema
}
entity_lower_bottom_resource={
    'datasource': {
        'source': 'entity',
        'projection': {
            'FileID': 1,
            'GlobalId': 1,
        },
    },
    'item_title': 'lowerBottom',
    'schema': entity_schema
}
entity_longger_extrusion_resource={
    'datasource': {
        'source': 'entity',
        'projection': {
            'FileID': 1,
            'GlobalId': 1,
        },
    },
    'item_title': 'longgerExtrusion',
    'schema': entity_schema
}
entity_parallel_bridge_resource={
    'datasource': {
        'source': 'entity',
        'projection': {
            'FileID': 1,
            'GlobalId': 1,
        },
    },
    'item_title': 'parallelBridge',
    'schema': entity_schema
}
entity_bigger_volume_resource={
    'datasource': {
        'source': 'entity',
        'projection': {
            'FileID': 1,
            'GlobalId': 1,
        },
    },
    'item_title': 'volumeBigger',
    'schema': entity_schema
}
entity_complete_above_resource={
    'datasource': {
        'source': 'entity',
        'projection': {
            'FileID': 1,
            'GlobalId': 1,
        },
    },
    'item_title': 'completeAbove',
    'schema': entity_schema
}
entity_closer_transverse_resource={
    'datasource': {
        'source': 'entity',
        'projection': {
            'FileID': 1,
            'GlobalId': 1,
        },
    },
    'item_title': 'closerTansverse',
    'schema': entity_schema
}
entity_closer_longitudinal_resource={
    'datasource': {
        'source': 'entity',
        'projection': {
            'FileID': 1,
            'GlobalId': 1,
        },
    },
    'item_title': 'closerLongi',
    'schema': entity_schema
}
entity_parallel_bridge_transverse_resource={
    'datasource': {
        'source': 'entity',
        'projection': {
            'FileID': 1,
            'GlobalId': 1,
        },
    },
    'item_title': 'parallelBridgeTransverse',
    'schema': entity_schema
}
entity_vertical_resource={
    'datasource': {
        'source': 'entity',
        'projection': {
            'FileID': 1,
            'GlobalId': 1,
        },
    },
    'item_title': 'Vertical',
    'schema': entity_schema
}
entity_overlap_z_resource={
    'datasource': {
        'source': 'entity',
        'projection': {
            'FileID': 1,
            'GlobalId': 1,
        },
    },
    'item_title': 'overlapZ',
    'schema': entity_schema
}
# below are old staff
###########################################

geometry_with_feature_resource={
    'item_title': 'GeometryWithFeatur',
    'schema': geometry_schema,
    'datasource': {
        'source': 'geometry',
    },
    'query_objectid_as_string':True,
}
geometry_with_entity_resource={
    'datasource': {
        'source': 'geometry',
    },
    'item_title': 'Shape',
    'schema': geometry_schema
}

geom_feature_search_resource = {
    'item_title': 'GeometryFeature',
    'schema': geom_feature_schema,
    'datasource': {
        'source': 'geometryFeature',
    },
    # 'query_objectid_as_string':True,
}

entity_relProperties_resource = {
    'datasource': {
        'source': 'entity',
        'filter': {
            "EntityType":"IfcRelDefinesByProperties"
        },
        'projection':{
            "Attribute":1,
        }
    },
    'item_title': 'IfcRelDefinesByProperties',
    'schema': entity_schema,
    'query_objectid_as_string':True,
} 
entity_withProperty_resource = {
    'datasource': {
        'source': 'entity',
        'projection':{
            "EntityType":1,
            "Attribute":1,
            'Links':1,
            'UserProperty':1,
        }
    },
    'item_title': 'EntityHasProperty',
    'schema': entity_schema,
}
entity_property_set_resource = {
    'datasource': {
        'source': 'entity',
        'filter': {"EntityType":"IfcPropertySet"},
        'projection': {
            'Attribute':1,
            'Links':1,
            'Properties':1,
        }
    },
    'item_title': 'PropertySet',
    'schema': entity_schema,
}
entity_simple_resource ={
    'datasource': {
        'source': 'entity',
        'projection':{
            "EntityType":1,
            "Attribute":1,
        }
    },
    'item_title': 'Property',
    'schema': entity_schema,
}


entity_guid_resource={
    'datasource': {
        'source': 'entity',
        'projection': {
            'Attribute': 1,
            'FileID': 1,
            'EntityType': 1,
        },
    },
    'item_title': 'Shape',
    'schema': entity_schema,
    # 'query_objectid_as_string':True,
}
entity_no_link_resource = {
    'datasource': {
        'source': 'entity',
        'filter': {"Links":[]},
    },
    'item_title': 'EntityHasNoLink',
    # 'query_objectid_as_string': True,
    # 'allow_unknown': True,
    'schema': entity_schema
}


query_schema = {
    'FileID': {
        'type': 'objectid',
        'data_relation': {
            'resource': 'file',
            'field': '_id',
            'embeddable': True
        },
    },
    'Resource': {'type': 'string'},
    'Clauses': {
        'type': 'list',
        'schema': {
            'type':'dict',
            'schema':{
                'Field': {'type': 'string'},
                'Variable': {'type': 'string'},
                'Value': {},
                'Operator': {'type':'string'}, 
            }
        }
    },
    'Description': {'type': 'string'},
}
query_resource = {
    'item_title': 'Query',
    'schema': query_schema,
}



trimbleToken_resource={
    'datasource': {
        'source': 'user',
        'projection': {
            'trimble_email': 1,
            'trimble_key': 1,
        },
    },
    'item_title': 'TrimbleToken',
    # 'query_objectid_as_string': True,
    # 'allow_unknown': True,
    'schema': user_schema
}
