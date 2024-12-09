**To Retrieve all of the fields and values of a single log event**

The following ``get-log-record`` example retrieves all of the fields and values of a single log event. ::

    aws logs get-log-record \
        --log-record-pointer "ClQKGAoUODc3MzYyMTE0MTkzOnRlc3ROSFQQBxI0GhgCBl9OTrgAAAABgsQLrwAGZJl0wAAAB4IgASjqz+P7+DEw6s/j+/gxOAFAL0j2BVClAhgAIAEQABgB"

Output::

    {
        "logRecord": {
            "@ingestionTime": "1716099017288",
            "@log": "123456789012:demo-log-group",
            "@logStream": "DemoStream",
            "@message": "Hello World",
            "@timestamp": "1716099016682"
        }
    }

For more information, see `Working with log groups and log streams <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Working-with-log-groups-and-streams.html>`__ in the *Amazon CloudWatch User Guide*.