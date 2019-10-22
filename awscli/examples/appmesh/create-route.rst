**Example 1: To create a new route with weighting**

The following ``create-route`` example uses a `JSON input file <https://docs.aws.amazon.com/cli/latest/userguide/cli-usage-skeleton.html>`__ to create a route with weighted targets. ::

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

The following ``create-route`` example uses a `JSON input file <https://docs.aws.amazon.com/cli/latest/userguide/cli-usage-skeleton.html>`__ to create a route with path-based routing. ::

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

**Example 3: To create a new route based on an HTTP header**

The following ``create-route`` example uses a `JSON input file <https://docs.aws.amazon.com/cli/latest/userguide/cli-usage-skeleton.html>`__ to create a route that will route all requests to ``serviceB`` that have any path prefix in an HTTPS post where the ``clientRequestId`` header has a prefix of ``123``::

    aws appmesh create-route \
        --cli-input-json file://create-route-headers.json

Contents of ``create-route-headers.json``::

    {
        "meshName" : "app1",
        "routeName" : "route-headers",
        "spec" : {
            "httpRoute" : {
                "action" : {
                    "weightedTargets" : [
                        {
                            "virtualNode" : "serviceB",
                            "weight" : 100
                        }
                    ]
                },
                "match" : {
                    "headers" : [
                        {
                            "invert" : false,
                            "match" : {
                                "prefix" : "123"
                            },
                            "name" : "clientRequestId"
                        }
                    ],
                    "method" : "POST",
                    "prefix" : "/",
                    "scheme" : "https"
                }
            }
        },
        "virtualRouterName" : "virtual-router1"
    }

Output::

    {
        "route": {
            "meshName": "app1",
            "metadata": {
                "arn": "arn:aws:appmesh:us-east-1:123456789012:mesh/app1/virtualRouter/virtual-router1/route/route-headers",
                "createdAt": 1565963028.608,
                "lastUpdatedAt": 1565963028.608,
                "uid": "a1b2c3d4-5678-90ab-cdef-11111EXAMPLE",
                "version": 1
            },
            "routeName": "route-headers",
            "spec": {
                "httpRoute": {
                    "action": {
                        "weightedTargets": [
                            {
                                "virtualNode": "serviceB",
                                "weight": 100
                            }
                        ]
                    },
                    "match": {
                        "headers": [
                            {
                                "invert": false,
                                "match": {
                                    "prefix": "123"
                                },
                                "name": "clientRequestId"
                            }
                        ],
                        "method": "POST",
                        "prefix": "/",
                        "scheme": "https"
                    }
                }
            },
            "status": {
                "status": "ACTIVE"
            },
            "virtualRouterName": "virtual-router1"
        }
    }

For more information, see `HTTP Headers <https://docs.aws.amazon.com/app-mesh/latest/userguide/route-http-headers.html>`__ in the *AWS App Mesh User Guide*.

**Example 4: To create a new route with a retry policy**

The following ``create-route`` example uses a JSON input file to create a route with a retry policy.::

    aws appmesh create-route \
        --cli-input-json file://create-route-retry-policy.json

Contents of ``create-route-retry-policy.json``::

    {
        "meshName": "App1",
        "routeName": "Route-retries1",
        "spec": {
            "httpRoute": {
                "action": {
                    "weightedTargets": [
                        {
                            "virtualNode": "ServiceB",
                            "weight": 100
                        }
                    ]
                },
                "match": {
                    "prefix": "/"
                },
                "retryPolicy": {
                    "perRetryTimeout": {
                        "value": 15,
                        "unit": "s"
                    },
                    "maxRetries": 3,
                    "httpRetryEvents": [
                        "server-error",
                        "gateway-error"
                    ],
                    "tcpRetryEvents": [
                        "connection-error"
                    ]
                }
            }
        },
        "virtualRouterName": "Virtual-router1"
    }

Output::

    {
        "route": {
            "meshName": "App1",
            "metadata": {
                "arn": "arn:aws:appmesh:us-east-1:123456789012:mesh/App1/virtualRouter/Virtual-router1/route/Route-retries1",
                "createdAt": 1568142345.942,
                "lastUpdatedAt": 1568142345.942,
                "uid": "a1b2c3d4-5678-90ab-cdef-11111EXAMPLE",
                "version": 1
            },
            "routeName": "Route-retries1",
            "spec": {
                "httpRoute": {
                    "action": {
                        "weightedTargets": [
                            {
                                "virtualNode": "ServiceB",
                                "weight": 100
                            }
                        ]
                    },
                    "match": {
                        "prefix": "/"
                    },
                    "retryPolicy": {
                        "httpRetryEvents": [
                            "server-error",
                            "gateway-error"
                        ],
                        "maxRetries": 3,
                        "perRetryTimeout": {
                            "unit": "s",
                            "value": 15
                        },
                        "tcpRetryEvents": [
                            "connection-error"
                        ]
                    }
                }
            },
            "status": {
                "status": "ACTIVE"
            },
            "virtualRouterName": "Virtual-router1"
        }
    }

For more information, see `Retry Policy <https://docs.aws.amazon.com/app-mesh/latest/userguide/route-retry-policy.html>`__ in the *AWS App Mesh User Guide*.
