**To Return the results from the specified query**

The following ``get-query-results`` example returns the results from the specified query. ::

    aws logs get-query-results \
        --query-id 82765b94-d048-4ef8-87c1-fd19a76a9d8e

Output::

    {
        "results": [
            [
                {
                    "field": "@timestamp",
                    "value": "2024-05-19 06:10:35.743"
                },
                {
                    "field": "@message",
                    "value": "Test BENCHMARK 3"
                },
                {
                    "field": "@logStream",
                    "value": "TestStream"
                },
                {
                    "field": "@ptr",
                    "value": "ClQKGAoUODc3MzYyMTE0MTkzOnRlc3ROSFQQARI0GhgCBmJoHCAAAAAAg5VGeQAGZJl2MAAAAQIgASjnpOT7+DEw3+Tk+/gxOAJAXkiwBlDfAhgAIAEQARgB"
                }
            ],
            [
                {
                    "field": "@timestamp",
                    "value": "2024-05-19 06:10:27.559"
                },
                {
                    "field": "@message",
                    "value": "Test BENCHMARK 2"
                },
                {
                    "field": "@logStream",
                    "value": "TestStream"
                },
                {
                    "field": "@ptr",
                    "value": "ClQKGAoUODc3MzYyMTE0MTkzOnRlc3ROSFQQARI0GhgCBmJoHCAAAAAAg5VGeQAGZJl2MAAAAQIgASjnpOT7+DEw3+Tk+/gxOAJAXkiwBlDfAhgAIAEQABgB"
                }
            ],
            [
                {
                    "field": "@timestamp",
                    "value": "2024-05-19 06:10:16.682"
                },
                {
                    "field": "@message",
                    "value": "Test BENCHMARK 1"
                },
                {
                    "field": "@logStream",
                    "value": "TestStream"
                },
                {
                    "field": "@ptr",
                    "value": "ClQKGAoUODc3MzYyMTE0MTkzOnRlc3ROSFQQBxI0GhgCBl9OTrgAAAABgsQLrwAGZJl0wAAAB4IgASjqz+P7+DEw6s/j+/gxOAFAL0j2BVClAhgAIAEQABgB"
                }
            ]
        ],
        "statistics": {
            "recordsMatched": 3.0,
            "recordsScanned": 3.0,
            "bytesScanned": 141.0
        },
        "status": "Complete"
    }

For more information, see `Analyzing log data with CloudWatch Logs Insights <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html>`__ in the *Amazon CloudWatch Logs User Guide*.