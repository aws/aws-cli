**To get your Amazon SES sending statistics**

The following ``get-send-statistics`` example returns your Amazon SES sending statistics. ::

    aws ses get-send-statistics

Output::

    {
        "SendDataPoints": [
            {
                "Complaints": 0,
                "Timestamp": "2013-06-12T19:32:00Z",
                "DeliveryAttempts": 2,
                "Bounces": 0,
                "Rejects": 0
            },
            {
                "Complaints": 0,
                "Timestamp": "2013-06-12T00:47:00Z",
                "DeliveryAttempts": 1,
                "Bounces": 0,
                "Rejects": 0
            }
        ]
    }


The result is a list of data points, representing the last two weeks of sending activity. Each data point in the list
contains statistics for a 15-minute interval.

In this example, there are only two data points because the only emails that the user sent in the last two weeks fell
within two 15-minute intervals.

For more information, see `Monitoring your Amazon SES sending activity <https://docs.aws.amazon.com/ses/latest/dg/monitor-sending-activity.html>`__ in the *Amazon Simple Email Service Developer Guide*.

