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
            "greengrassGroupId": "01d04b07-2a51-467f-9d03-0c90b3cdcaaf",
            "greengrassGroupVersionId": "731b371d-d644-4b67-ac64-3934e99b75d7"
        }
    }
