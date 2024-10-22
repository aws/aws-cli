**To list all log pattern sets**

This example uses the ``list-log-pattern-sets`` command to list all log pattern sets in an application. ::

    aws application-insights list-log-pattern-sets \
        --resource-group-name MYEC2

Output::

    {
        "ResourceGroupName": "MYEC2",
        "AccountId": "123456789012",
        "LogPatternSets": ["SAMPLE"]
    }