**To retrieve the top contributor data on workload insights**

The following ``get-query-results-workload-insights-top-contributors-data`` example returns the data for the specified query. ::

    aws networkflowmonitor get-query-results-workload-insights-top-contributors-data \
        --scope-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --query-id a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "datapoints": [
            {
                "timestamps": [
                    "2024-12-09T19:00:00+00:00",
                    "2024-12-09T19:05:00+00:00",
                    "2024-12-09T19:10:00+00:00"
                ],
                "values": [
                    259943.0,
                    194856.0,
                    216432.0
                ],
                "label": "use1-az6"
            }
        ],
        "unit": "Bytes"
    }

For more information, see `Evaluate network flows with workload insights <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-NetworkFlowMonitor-configure-evaluate-flows.html>`__ in the *Amazon CloudWatch User Guide*.