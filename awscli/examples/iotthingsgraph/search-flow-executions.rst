**To search for flow executions**

The following ``search-flow-executions`` example search for all executions of a flow in a specified system instance. ::

    aws iotthingsgraph search-flow-executions \
        --system-instance-id "urn:tdm:us-west-2/123456789012/default:Deployment:Room218"

Output::

    {
        "summaries": [
            {
                "createdAt": 1559247540.656,
                "flowExecutionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "flowTemplateId": "urn:tdm:us-west-2/123456789012/default:Workflow:MyFlow",
                "status": "RUNNING ",
                "systemInstanceId": "urn:tdm:us-west-2/123456789012/default:System:MySystem",
                "updatedAt": 1559247540.656
            }
        ]
    }
