**To Return a list of the fields that are included in log events in the specified log group**

The following ``get-log-group-fields`` example returns a list of the fields that are included in log events in the specified log group. ::

    aws logs get-log-group-fields \
        --log-group-name demo-log-group

Output::

    {
        "logGroupFields": []
    }

For more information, see `Working with log groups and log streams <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Working-with-log-groups-and-streams.html>`__ in the *Amazon CloudWatch User Guide*.