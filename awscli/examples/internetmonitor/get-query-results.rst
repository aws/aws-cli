**To fetch the results of a query**

This example uses the ``get-query-results`` command to fetch the results of a query performed in a monitor. ::

    aws internetmonitor get-query-results \
        --monitor-name TestMonitor \
        --query-id AQICAHjE50ADcWtUTXGTlgtIHH4U_u4xxxxxx

Output::

    {
        "Fields": [{
            "Name": "timestamp",
            "Type": "integer"
        }, {
            "Name": "availability",
            "Type": "float"
        }, {
            "Name": "performance",
            "Type": "float"
        }, {
            "Name": "rtt_p50",
            "Type": "bigint"
        }, {
            "Name": "rtt_p90",
            "Type": "bigint"
        }, {
            "Name": "rtt_p95",
            "Type": "bigint"
        }, {
            "Name": "bytes_in",
            "Type": "bigint"
        }, {
            "Name": "bytes_out",
            "Type": "bigint"
        }],
        "Data": [
            ["1724833200", "100.0", "100.0", "26", "68", "72", "1258", "120"]
        ]
    }