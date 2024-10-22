**To create a log pattern and add it to a log pattern set**

This example uses the ``create-log-pattern`` command to add an log pattern to a log pattern set. ::

    aws application-insights create-log-pattern \
        --resource-group-name MYEC2 \
        --pattern-set-name SAMPLE \
        --pattern-name new 
        --pattern error 
        --rank 750000

Output::

    {
        "LogPattern": {
            "PatternSetName": "SAMPLE",
            "PatternName": "new",
            "Pattern": "error",
            "Rank": 750000
        },
        "ResourceGroupName": "MYEC2"
    }