**To undeploy a system instance from its target**

The following ``undeploy-system-instance`` example removes a system instance from its target. ::

    aws iotthingsgraph undeploy-system-instance \
        --id "urn:tdm:us-west-2/123456789012/default:Deployment:Room215"

Output::

    {
        "summary": {
            "id": "urn:tdm:us-west-2/123456789012/default:Deployment:Room215",
            "arn": "arn:aws:iotthingsgraph:us-west-2:123456789012:Deployment/default/Room215",
            "status": "PENDING_DELETE",
            "target": "GREENGRASS",
            "greengrassGroupName": "ThingsGraphGrnGr",
            "createdAt": 1553189694.255,
            "updatedAt": 1559344549.601,
            "greengrassGroupId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "greengrassGroupVersionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
        }
    }
