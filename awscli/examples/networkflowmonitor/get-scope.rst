**To retrieve information about a scope**

The following ``get-scope`` example displays information about a scope, such as status, tags, name and target details. ::

    aws networkflowmonitor get-scope \
        --scope-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "scopeId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "status": "SUCCEEDED",
        "scopeArn": "arn:aws:networkflowmonitor:us-west-2:123456789012:scope/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "targets": [
            {
                "targetIdentifier": {
                    "targetId": {
                        "accountId": "123456789012"
                    },
                    "targetType": "ACCOUNT"
                },
                "region": "us-west-2"
            }
        ],
        "tags": {}
    }

For more information, see `Components and features of Network Flow Monitor <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-NetworkFlowMonitor-components.html>`__ in the *Amazon CloudWatch User Guide*.