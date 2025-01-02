**To retrieve the Top Contributor data on Workload insights**

The following ``get-query-results-workload-insights-top-contributors-data`` example returns the data for the specified query. ::

    aws networkflowmonitor get-query-results-workload-insights-top-contributors-data \
        --scope-id e21cda79-30a0-4c12-9299-d8629d76d8cf \
        --query-id cc4f4ab3-3103-33b8-80ff-d6597a0c6cea

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