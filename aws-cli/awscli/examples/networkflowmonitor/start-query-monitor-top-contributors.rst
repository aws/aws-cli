**To start a query**

The following ``start-query-monitor-top-contributors`` example starts the query which returns a query ID to retrieve the top contributors. ::

    aws networkflowmonitor start-query-monitor-top-contributors \
        --monitor-name Demo \
        --start-time 2024-12-09T19:00:00Z \
        --end-time 2024-12-09T19:15:00Z \
        --metric-name DATA_TRANSFERRED \
        --destination-category UNCLASSIFIED

Output::

    {
        "queryId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Evaluate network flows with workload insights <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-NetworkFlowMonitor-configure-evaluate-flows.html>`__ in the *Amazon CloudWatch User Guide*.