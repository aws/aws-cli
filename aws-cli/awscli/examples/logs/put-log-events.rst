**To put log events into a log stream**

The following ``put-log-events`` example puts log events to a log stream named ``20150601`` in the log group ``my-logs``. The command reads a JSON array of events from a file named ``events`` in the current directory. ::

    aws logs put-log-events \
        --log-group-name my-logs \
        --log-stream-name 20150601 \
        --log-events file://events

Contents of ``events``::

    [
        {
            "timestamp": 1433190184356,
            "message": "Example Event 1"
        },
        {
            "timestamp": 1433190184358,
            "message": "Example Event 2"
        },
        {
            "timestamp": 1433190184360,
            "message": "Example Event 3"
        }
    ]

Output::

    {
        "nextSequenceToken": "49542672486831074009579604567656788214806863282469607346"
    }

Each subsequent call requires the next sequence token provided by the previous call to be specified with the sequence token option. ::

    aws logs put-log-events \
        --log-group-name my-logs \
        --log-stream-name 20150601 \
        --log-events file://events2 \
        --sequence-token "49542672486831074009579604567656788214806863282469607346"

Contents of ``events2``::

    [
        {
            "timestamp": 1433190184362,
            "message": "Example Event 4"
        },
        {
            "timestamp": 1433190184364,
            "message": "Example Event 5"
        }
    ]

Output::

    {
        "nextSequenceToken": "49542672486831074009579604567900991230369019956308219826"
    }

For more information, see `Working with log groups and log streams <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Working-with-log-groups-and-streams.html>`__ in the *Amazon CloudWatch Logs User Guide*.
