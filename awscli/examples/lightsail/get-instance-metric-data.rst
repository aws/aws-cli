**To get instance NetworkOut metric data for a month period**

The following ``get-instance-metric-data`` example outputs the total ``NetworkOut`` metric data in bytes for an approximate month-long period.

We recommend that you use an epoch time converter to identify the start and end times. If the time between the ``--start-time`` and ``--end-time`` is greater than 2628000 seconds (approximately one month), then multiple results are returned for each 2628000 interval, as shown in the following sample response. ::

    aws lightsail get-instance-metric-data \
        --instance-name InstanceName \
        --metric-name NetworkOut \
        --period 2628000 \
        --start-time 1546304400 \
        --end-time 1577840400 
        --unit Bytes 
        --statistics Sum

Output::

    {
        "metricData": [
            {
                "timestamp": 1556812800.0,
                "sum": 22359134.0,
                "unit": "Bytes"
            },
            {
                "timestamp": 1554184800.0,
                "sum": 5968238.0,
                "unit": "Bytes"
            }
        ],
        "metricName": "NetworkOut"
    }
