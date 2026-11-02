**To retrieve query statistics**

The following ``get-query-statistics`` example retrieves statistics on the planning and execution of a query. ::

    aws lakeformation get-query-statistics \
        --query-id='a1b2c3d4-5678-90ab-cdef-EXAMPLE11111' 

Output::

    {
        "ExecutionStatistics": {
            "AverageExecutionTimeMillis": 0,
            "DataScannedBytes": 0,
            "WorkUnitsExecutedCount": 0
        },
        "PlanningStatistics": {
            "EstimatedDataToScanBytes": 43235,
            "PlanningTimeMillis": 2377,
            "QueueTimeMillis": 440,
            "WorkUnitsGeneratedCount": 1
        },
        "QuerySubmissionTime": "2022-08-11T02:14:38.641870+00:00"
    }
