**To update a log pattern in a log pattern set**

This example uses the ``update-log-pattern`` command to update the log pattern in a log pattern set. ::

    aws application-insights update-log-pattern \
        --resource-group-name testgroup \
        --pattern-set-name Test \
        --pattern-name newpattern \
        --pattern ERROR \
        --rank 2

Output::

    {
        "ResourceGroupName": "testgroup",
        "LogPattern": {
            "PatternSetName": "Test",
            "PatternName": "newpattern",
            "Pattern": "ERROR",
            "Rank": 2
        }
    }