**To start a new query in an internet monitor**

This example uses the ``start-query`` command to start a new query in an internet monitor. ::

    aws internetmonitor start-query \
        --monitor-name TestMonitor \
        --start-time 2024-08-27T00:00:00Z \
        --end-time 2024-08-28T00:00:00Z \
        --filter-parameters Field=country,Operator=EQUALS,Values="United States" Field=geo,Values=city \
        --query-type TOP_LOCATIONS

Output::

    {
        "QueryId": "AQICAHjE50ADcWtUTXGTlgtIHH4U_uxxxxxxxx"
    }