**To get an organization recommendation**

The following ``get-organization-recommendation`` example gets an organization recommendation by its identifier. ::

    aws trustedadvisor get-organization-recommendation \
        --organization-recommendation-identifier arn:aws:trustedadvisor:::organization-recommendation/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "organizationRecommendation": {
            "arn": "arn:aws:trustedadvisor:::organization-recommendation/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "name": "Lambda Runtime Deprecation Warning",
            "description": "One or more lambdas are using a deprecated runtime",
            "awsServices": [
                "lambda"
            ],
            "checkArn": "arn:aws:trustedadvisor:::check/L4dfs2Q4C5",
            "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "lifecycleStage": "resolved",
            "pillars": [
                "security"
            ],
            "resourcesAggregates": {
                "errorCount": 0,
                "okCount": 0,
                "warningCount": 0
            },
            "source": "ta_check",
            "status": "warning",
            "type": "priority"
        }
    }

For more information, see `Get started with the Trusted Advisor API <https://docs.aws.amazon.com/awssupport/latest/user/get-started-with-aws-trusted-advisor-api.html>`__ in the *AWS Trusted Advisor User Guide*.