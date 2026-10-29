**To search for system instances**

The following ``search-system-instances`` example searches for all system instances that contain the specified system. ::

    aws iotthingsgraph search-system-instances \
        --filters name="SYSTEM_TEMPLATE_ID",value="urn:tdm:us-west-2/123456789012/default:System:SecurityFlow"

Output::

    {
        "summaries": [
            {
                "id": "urn:tdm:us-west-2/123456789012/default:Deployment:DeploymentForSample",
                "arn": "arn:aws:iotthingsgraph:us-west-2:123456789012:Deployment/default/DeploymentForSample",
                "status": "NOT_DEPLOYED",
                "target": "GREENGRASS",
                "greengrassGroupName": "ThingsGraphGrnGr",
                "createdAt": 1555716314.707,
                "updatedAt": 1555716314.707
            },
            {
                "id": "urn:tdm:us-west-2/123456789012/default:Deployment:MockDeployment",
                "arn": "arn:aws:iotthingsgraph:us-west-2:123456789012:Deployment/default/MockDeployment",
                "status": "DELETED_IN_TARGET",
                "target": "GREENGRASS",
                "greengrassGroupName": "ThingsGraphGrnGr",
                "createdAt": 1549416462.049,
                "updatedAt": 1549416722.361,
                "greengrassGroupId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "greengrassGroupVersionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
            },
            {
                "id": "urn:tdm:us-west-2/123456789012/default:Deployment:MockDeployment2",
                "arn": "arn:aws:iotthingsgraph:us-west-2:123456789012:Deployment/default/MockDeployment2",
                "status": "DEPLOYED_IN_TARGET",
                "target": "GREENGRASS",
                "greengrassGroupName": "ThingsGraphGrnGr",
                "createdAt": 1549572385.774,
                "updatedAt": 1549572418.408,
                "greengrassGroupId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "greengrassGroupVersionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333"
            },
            {
                "id": "urn:tdm:us-west-2/123456789012/default:Deployment:Room215",
                "arn": "arn:aws:iotthingsgraph:us-west-2:123456789012:Deployment/default/Room215",
                "status": "NOT_DEPLOYED",
                "target": "GREENGRASS",
                "greengrassGroupName": "ThingsGraphGG",
                "createdAt": 1547056918.413,
                "updatedAt": 1547056918.413
            },
            {
                "id": "urn:tdm:us-west-2/123456789012/default:Deployment:Room218",
                "arn": "arn:aws:iotthingsgraph:us-west-2:123456789012:Deployment/default/Room218",
                "status": "NOT_DEPLOYED",
                "target": "CLOUD",
                "createdAt": 1559249315.208,
                "updatedAt": 1559249315.208
            }
        ]
    }
