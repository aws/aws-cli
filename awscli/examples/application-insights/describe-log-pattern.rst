**To describe a log pattern from a log pattern set**

This example uses the ``describe-log-pattern`` command to describe a log pattern from a log pattern set. ::

    aws application-insights describe-log-pattern \
        --resource-group-name MYEC2 \
        --pattern-set-name SAMPLE \
        --pattern-name new2

Output::

    {
        "ResourceGroupName": "MYEC2",
        "AccountId": "123456789012",
        "LogPattern": {
            "PatternSetName": "SAMPLE",
            "PatternName": "new2",
            "Pattern": "error",
            "Rank": 750000
        }
    }