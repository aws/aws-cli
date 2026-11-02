**To return a list of allowed node type updates**

The following ``list-allowed-node-type-updates`` example returns a list of available node type updates. ::

    aws memorydb list-allowed-node-type-updates \
        --cluster-name my-cluster

Output::

    {
        "ScaleUpNodeTypes": [
            "db.r6g.xlarge",
            "db.r6g.2xlarge",
            "db.r6g.4xlarge"
        ],
        "ScaleDownNodeTypes": [
            "db.t4g.medium"
        ]
    }

For more information, see `Scaling <https://docs.aws.amazon.com/memorydb/latest/devguide/scaling.html>`__ in the *MemoryDB User Guide*.
