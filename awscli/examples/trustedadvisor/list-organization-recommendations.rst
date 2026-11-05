**Example 1: To list organization recommendations**

The following ``list-organization-recommendations`` example lists all organization recommendations and does not include a filter. ::

    aws trustedadvisor list-organization-recommendations

Output::

    {
        "organizationRecommendationSummaries": [
            {
                "arn": "arn:aws:trustedadvisor:::organization-recommendation/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "name": "Lambda Runtime Deprecation Warning",
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
            },
            {
                "arn": "arn:aws:trustedadvisor:::organization-recommendation/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "name": "Lambda Runtime Deprecation Warning",
                "awsServices": [
                    "lambda"
                ],
                "checkArn": "arn:aws:trustedadvisor:::check/L4dfs2Q4C5",
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
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
        ],
        "nextToken": "REDACTED"
    }

For more information, see `Get started with the Trusted Advisor API <https://docs.aws.amazon.com/awssupport/latest/user/get-started-with-aws-trusted-advisor-api.html>`__ in the *AWS Trusted Advisor User Guide*.

**Example 2: To list organization recommendations with a filter**

The following ``list-organization-recommendations`` example filters and returns a max of one organization recommendation that is a part of the "security" pillar. ::

    aws trustedadvisor list-organization-recommendations \
        --pillar security \
        --max-items 100

Output::

    {
        "organizationRecommendationSummaries": [{
            "arn": "arn:aws:trustedadvisor:::organization-recommendation/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "name": "Lambda Runtime Deprecation Warning",
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
        }],
        "nextToken": "REDACTED"
    }

For more information, see `Get started with the Trusted Advisor API <https://docs.aws.amazon.com/awssupport/latest/user/get-started-with-aws-trusted-advisor-api.html>`__ in the *AWS Trusted Advisor User Guide*.

**Example 3: To list organization recommendations with a pagination token**

The following ``list-organization-recommendations`` example uses the "nextToken" returned from a previous request to fetch the next page of organization recommendations. ::

    aws trustedadvisor list-organization-recommendations \
        --pillar security \
        --max-items 100 \
        --starting-token <next-token>

Output::

    {
        "organizationRecommendationSummaries": [{
            "arn": "arn:aws:trustedadvisor:::organization-recommendation/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "name": "Lambda Runtime Deprecation Warning",
            "awsServices": [
                "lambda"
            ],
            "checkArn": "arn:aws:trustedadvisor:::check/L4dfs2Q4C5",
            "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
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
        }]
    }

For more information, see `Get started with the Trusted Advisor API <https://docs.aws.amazon.com/awssupport/latest/user/get-started-with-aws-trusted-advisor-api.html>`__ in the *AWS Trusted Advisor User Guide*.