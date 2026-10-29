**To retrieve the status of the query**

The following ``get-query-status-monitor-top-contributors`` example displays the current status of the query in the specified account. ::

    aws networkflowmonitor get-query-status-monitor-top-contributors \
        --monitor-name Demo \
        --query-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "status": "SUCCEEDED"
    }

For more information, see `Evaluate network flows with workload insights <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-NetworkFlowMonitor-configure-evaluate-flows.html>`__ in the *Amazon CloudWatch User Guide*.