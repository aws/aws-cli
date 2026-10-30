**To return a list of engine versions**

The following ``describe-engine-versions`` example returns a list of engine versions. ::

    aws memorydb describe-engine-versions

Output::

    {
        "EngineVersions": [
            {
                "EngineVersion": "6.2",
                "EnginePatchVersion": "6.2.6",
                "ParameterGroupFamily": "memorydb_redis6"
            }
        ]
    }

For more information, see `Engine versions <https://docs.aws.amazon.com/memorydb/latest/devguide/engine-versions.html>`__ in the *MemoryDB User Guide*.
