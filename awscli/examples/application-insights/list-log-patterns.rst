**To list all log patterns in a log pattern set**

This example uses the ``list-log-patterns`` command to lists all the log patterns in a log pattern set. ::

    aws application-insights list-log-patterns \
        --resource-group-name MYEC2

Output::

    {
        "ResourceGroupName": "MYEC2",
        "AccountId": "123456789012",
        "LogPatterns": [{
            "PatternSetName": "SAMPLE",
            "PatternName": "new",
            "Pattern": "error",
            "Rank": 1
        }, {
            "PatternSetName": "SAMPLE",
            "PatternName": "new2",
            "Pattern": "error",
            "Rank": 750000
        }]
    }