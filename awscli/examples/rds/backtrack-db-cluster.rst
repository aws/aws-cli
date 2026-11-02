**To backtrack an Aurora DB cluster**

The following ``backtrack-db-cluster`` example backtracks the specified DB cluster sample-cluster to March 19, 2018, at 10 a.m. :: 

    aws rds backtrack-db-cluster \
        --db-cluster-identifier sample-cluster \
        --backtrack-to 2018-03-19T10:00:00+00:00

Output::

    {
        "DBClusterIdentifier": "sample-cluster",
        "BacktrackIdentifier": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "BacktrackTo": "2018-03-19T10:00:00+00:00",
        "BacktrackedFrom": "2018-03-19T11:30:00.123000+00:00",
        "BacktrackRequestCreationTime": "2018-03-19T11:30:00.123000+00:00",
        "Status": "PENDING"
    }

For more information, see `Backtracking an Aurora DB cluster <https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraMySQL.Managing.Backtrack.html>`__ in the *Amazon Aurora User Guide*.
