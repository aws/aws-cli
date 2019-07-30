**Example 1: To create a new route with weighting**

The following ``create-route`` example uses a JSON input file to create a route with weighted targets. ::

    aws appmesh create-route \
        --cli-input-json file://create-route-weighted.json

Contents of ``create-route-weighted.json``::

    {
        "meshName" : "app1",
        "routeName" : "toVnServiceB-weighted",
        "spec" : {
            "httpRoute" : {
                "action" : {
                    "weightedTargets" : [
                        {
                            "virtualNode" : "vnServiceBv1",
                            "weight" : 90
                        },
                        {
                            "virtualNode" : "vnServiceBv2",
                            "weight" : 10
                        }
                    ]
                },
                "match" : {
                    "prefix" : "/"
                }
            }
        },
        "virtualRouterName" : "vrServiceB"
    }

Output::

    {
        "route": {
            "meshName": "app1",
            "metadata": {
                "arn": "arn:aws:appmesh:us-east-1:123456789012:mesh/app1/virtualRouter/vrServiceB/route/toVnServiceB-weighted",
                "createdAt": 1563811384.015,
                "lastUpdatedAt": 1563811384.015,
                "uid": "a1b2c3d4-5678-90ab-cdef-11111EXAMPLE",
                "version": 1
            },
            "routeName": "toVnServiceB-weighted",
            "spec": {
                "httpRoute": {
                    "action": {
                        "weightedTargets": [
                            {
                                "virtualNode": "vnServiceBv1",
                                "weight": 90
                            },
                            {
                                "virtualNode": "vnServiceBv2",
                                "weight": 10
                            }
                        ]
                    },
                    "match": {
                        "prefix": "/"
                    }
                }
            },
            "status": {
                "status": "ACTIVE"
            },
            "virtualRouterName": "vrServiceB"
        }
    }

For more information, see `Routes <https://docs.aws.amazon.com/app-mesh/latest/userguide/routes.html>`__ in the *AWS App Mesh User Guide*.

**Example 2: To create a new route with path-based routing**

The following ``create-route`` example uses a JSON input file to create a route with path-based routing. ::

    aws appmesh create-route \
        --cli-input-json file://create-route-path.json

Contents of ``create-route-path.json``::

    {
        "meshName": "app1",
        "routeName": "toVnServiceB-path",
        "spec": {
            "httpRoute": {
                "action": {
                    "weightedTargets": [
                        {
                            "virtualNode": "vnServiceBv1",
                            "weight": 100
                        }
                    ]
                },
                "match": {
                    "prefix": "/metrics"
                }
            }
        },
        "virtualRouterName": "vrServiceB"
    }
    
Output::

    {
        "route": {
            "meshName": "app1",
            "metadata": {
                "arn": "arn:aws:appmesh:us-east-1:123456789012:mesh/app1/virtualRouter/vrServiceB/route/toVnServiceB-path",
                "createdAt": 1563823638.831,
                "lastUpdatedAt": 1563823638.831,
                "uid": "a1b2c3d4-5678-90ab-cdef-11111EXAMPLE",
                "version": 1
            },
            "routeName": "toVnServiceB-path",
            "spec": {
                "httpRoute": {
                    "action": {
                        "weightedTargets": [
                            {
                                "virtualNode": "vnServiceBv1",
                                "weight": 100
                            }
                        ]
                    },
                    "match": {
                        "prefix": "/metrics"
                    }
                }
            },
            "status": {
                "status": "ACTIVE"
            },
            "virtualRouterName": "vrServiceB"
        }
    }

For more information, see `Path-based Routing <https://docs.aws.amazon.com/app-mesh/latest/userguide/route-path.html>`__ in the *AWS App Mesh User Guide*.
