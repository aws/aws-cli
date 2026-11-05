**To return a list of parameter groups**

The following ``describe-parameter-groups`` example returns a list of parameter groups. ::

    aws memorydb describe-parameter-groups

Output::

    {
        "ParameterGroups": [
            {
                "Name": "default.memorydb-redis6",
                "Family": "memorydb_redis6",
                "Description": "Default parameter group for memorydb_redis6",
                "ARN": "arn:aws:memorydb:us-west-2:491658xxxxxx:parametergroup/default.memorydb-redis6"
            }
        ]
    }

For more information, see `Configuring engine parameters using parameter groups <https://docs.aws.amazon.com/memorydb/latest/devguide/parametergroups.html>`__ in the *MemoryDB User Guide*.
