**To retrieve a list of scopes**

The following ``list-scopes`` example lists all scopes in the specified account. ::

    aws networkflowmonitor list-scopes 

Output::

    {
        "scopes": [
            {
                "scopeId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "status": "SUCCEEDED",
                "scopeArn": "arn:aws:networkflowmonitor:us-west-2:123456789012:scope/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
            }
        ]
    }

For more information, see `Components and features of Network Flow Monitor <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-NetworkFlowMonitor-components.html>`__ in the *Amazon CloudWatch User Guide*.