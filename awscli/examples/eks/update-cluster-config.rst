**Example 1: To update cluster endpoint access**

The following ``update-cluster-config`` example updates a cluster to disable endpoint public access and enable private endpoint access. ::

    aws eks update-cluster-config \
        --name example \
        --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true

Output::

    {
        "update": {
            "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "status": "InProgress",
            "type": "EndpointAccessUpdate",
            "params": [
                {
                    "type": "EndpointPublicAccess",
                    "value": "false"
                },
                {
                    "type": "EndpointPrivateAccess",
                    "value": "true"
                }
            ],
            "createdAt": 1565806986.506,
            "errors": []
        }
    }

For more information, see `Cluster API server endpoint <https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html>`__ in the *Amazon EKS User Guide*.

**Example 2: To enable logging for a cluster**

The following ``update-cluster-config`` example enables all cluster control plane logging types for a cluster named ``example``. ::

    aws eks update-cluster-config \
        --name example \
        --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'

Output::

    {
        "update": {
            "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "status": "InProgress",
            "type": "LoggingUpdate",
            "params": [
                {
                    "type": "ClusterLogging",
                    "value": "{\"clusterLogging\":[{\"types\":[\"api\",\"audit\",\"authenticator\",\"controllerManager\",\"scheduler\"],\"enabled\":true}]}"
                }
            ],
            "createdAt": 1565807210.37,
            "errors": []
        }
    }

For more information, see `Send control plane logs to CloudWatch Logs <https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html>`__ in the *Amazon EKS User Guide*.
