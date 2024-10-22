**To describe the status of an existing query**

This example uses the ``get-query-status`` command to get a query's current status in an internet monitor. ::

    aws internetmonitor get-query-status \
        --monitor-name TestTCP \
        --query-id AQICAHjE50ADcWtUTXGTlgtIHH4U_u4xxxxxx

Output::

    {
        "Status": "SUCCEEDED"
    }