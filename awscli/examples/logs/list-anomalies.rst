**To Returns a list of anomalies**

The following ``list-anomalies`` example returns a list of anomalies that log anomaly detectors have found. ::

    aws logs list-anomalies

Output::

    {
        "anomalies": [
            {
                "anomalyId": "a1b2c3d4-5678-90ab-cdef-example11111",
                "patternId": "12345678901abc12345def1a2b3c4d5f",
                "anomalyDetectorArn": "arn:aws:logs:us-east-1:123456789012:anomaly-detector:a1b2c3d4-5678-90ab-cdef-example11111",
                "patternString": "REPORT RequestId: <*>\tDuration: <*> ms\tBilled Duration: <*> ms\tMemory Size: <*> MB\tMax Memory Used: <*> MB\tInit Duration: <*> ms\t\n",
                "patternRegex": "\\QREPORT RequestId: \\E.*\\Q\tDuration: \\E.*\\Q ms\tBilled Duration: \\E.*\\Q ms\tMemory Size: \\E.*\\Q MB\tMax Memory Used: \\E.*\\Q MB\tInit Duration: \\E.*\\Q ms\t\n\\E",
                "priority": "LOW",
                "firstSeen": 1727631180000,
                "lastSeen": 1727631480000,
                "description": "Unexpected value 508 for Duration 3",
                "active": false,
                "state": "Active",
                "histogram": {
                    "1727631180000": 1
                },
                "logSamples": [
                    {
                        "timestamp": 1727631190662,
                        "message": "REPORT RequestId: a1b2c3d4-5678-90ab-cdef-example11111\tDuration: 507.04 ms\tBilled Duration: 508 ms\tMemory Size: 256 MB\tMax Memory Used: 98 MB\tInit Duration: 1075.35 ms\t\n"
                    }
                ],
                "patternTokens": [
                    {
                        "dynamicTokenPosition": 0,
                        "isDynamic": false,
                        "tokenString": "REPORT",
                        "enumerations": {}
                    },
                    {
                        "dynamicTokenPosition": 1,
                        "isDynamic": true,
                        "tokenString": "<*>",
                        "enumerations": {
                            "a1b2c3d4-5678-90ab-cdef-example11111": 1
                        }
                    },
                    {
                        "dynamicTokenPosition": 3,
                        "isDynamic": true,
                        "tokenString": "<*>",
                        "enumerations": {
                            "508": 1
                        }
                    },
                    {
                        "dynamicTokenPosition": 4,
                        "isDynamic": true,
                        "tokenString": "<*>",
                        "enumerations": {
                            "256": 1
                        }
                    },
                    {
                        "dynamicTokenPosition": 0,
                        "isDynamic": false,
                        "tokenString": " ",
                        "enumerations": {}
                    },
                    {
                        "dynamicTokenPosition": 5,
                        "isDynamic": true,
                        "tokenString": "<*>",
                        "enumerations": {
                            "98": 1
                        }
                    },
                    {
                        "dynamicTokenPosition": 6,
                        "isDynamic": true,
                        "tokenString": "<*>",
                        "enumerations": {
                            "1075.35": 1
                        }
                    },
                    {
                        "dynamicTokenPosition": 0,
                        "isDynamic": false,
                        "tokenString": "\n",
                        "enumerations": {}
                    }
                ],
                "logGroupArnList": [
                    "arn:aws:logs:us-east-1:123456789012:log-group:demo-log-group"
                ],
                "suppressed": false,
                "suppressedDate": 0,
                "suppressedUntil": 0,
                "isPatternLevelSuppression": false
            }
        ]
    }

For more information, see `Log anomaly detection <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/LogsAnomalyDetection.html>`__ in the *Amazon CloudWatch Logs User Guide*.