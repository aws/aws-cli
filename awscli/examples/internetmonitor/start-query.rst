**To start a new query in an internet monitor**

The following ``start-query`` example starts a new query in an internet monitor. ::

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

For more information, see `Use the Internet Monitor query interface <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-IM-view-cw-tools-cwim-query.html>`__ in the *Amazon CloudWatch User Guide*.
