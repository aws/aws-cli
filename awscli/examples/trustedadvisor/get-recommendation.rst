**To get a recommendation**

The following ``get-recommendation`` example gets a recommendation by its identifier. ::

    aws trustedadvisor get-recommendation \
        --recommendation-identifier arn:aws:trustedadvisor::123456789012:recommendation/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "recommendation": {
            "arn": "arn:aws:trustedadvisor::123456789012:recommendation/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "name": "MFA Recommendation",
            "description": "Enable multi-factor authentication",
            "awsServices": [
                "iam"
            ],
            "checkArn": "arn:aws:trustedadvisor:::check/7DAFEmoDos",
            "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "lastUpdatedAt": "2023-11-01T15:57:58.673Z",
            "pillarSpecificAggregates": {
                "costOptimizing": {
                    "estimatedMonthlySavings": 0.0,
                    "estimatedPercentMonthlySavings": 0.0
                }
            },
            "pillars": [
                "security"
            ],
            "resourcesAggregates": {
                "errorCount": 1,
                "okCount": 0,
                "warningCount": 0
            },
            "source": "ta_check",
            "status": "error",
            "type": "standard"
        }
    }

For more information, see `Get started with the Trusted Advisor API <https://docs.aws.amazon.com/awssupport/latest/user/get-started-with-aws-trusted-advisor-api.html>`__ in the *AWS Trusted Advisor User Guide*.