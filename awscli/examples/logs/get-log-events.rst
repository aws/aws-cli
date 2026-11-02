**To get log events from a log stream**

The following ``get-log-events`` example retrieves log events from a log stream named ``20150601`` in the log group ``my-logs``. ::

    aws logs get-log-events \
        --log-group-name my-logs \
        --log-stream-name 20150601

Output::

    {
        "nextForwardToken": "f/31961209122447488583055879464742346735121166569214640130",
        "events": [
            {
                "ingestionTime": 1433190494190,
                "timestamp": 1433190184356,
                "message": "Example Event 1"
            },
            {
                "ingestionTime": 1433190516679,
                "timestamp": 1433190184356,
                "message": "Example Event 1"
            },
            {
                "ingestionTime": 1433190494190,
                "timestamp": 1433190184358,
                "message": "Example Event 2"
            }
        ],
        "nextBackwardToken": "b/31961209122358285602261756944988674324553373268216709120"
    }

For more information, see `Working with log groups and log streams <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Working-with-log-groups-and-streams.html#ViewingLogData>`__ in the *Amazon CloudWatch Logs User Guide*.
