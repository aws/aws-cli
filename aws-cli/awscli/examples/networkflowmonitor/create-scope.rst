**To create a scope**

The following ``create-scope`` example creates a scope that includes a set of resources for which Network Flow Monitor will generate network traffic metrics. ::

    aws networkflowmonitor create-scope \
        --targets '[{"targetIdentifier":{"targetId":{"accountId":"123456789012"},"targetType":"ACCOUNT"},"region":"us-west-2"}]'

Output::

    {
        "scopeId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "status": "IN_PROGRESS",
        "tags": {}
    }

For more information, see `Components and features of Network Flow Monitor <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-NetworkFlowMonitor-components.html>`__ in the *Amazon CloudWatch User Guide*.