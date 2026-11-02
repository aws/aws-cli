**To list organization recommendation accounts**

The following ``list-organization-recommendation-accounts`` example lists all account recommendation summaries for an organization recommendation by its identifier. ::

    aws trustedadvisor list-organization-recommendation-accounts \
        --organization-recommendation-identifier arn:aws:trustedadvisor:::organization-recommendation/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "accountRecommendationLifecycleSummaries": [{
            "accountId": "123456789012",
            "accountRecommendationArn": "arn:aws:trustedadvisor::123456789012:recommendation/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "lifecycleStage": "resolved",
            "updateReason": "Resolved issue",
            "updateReasonCode": "valid_business_case",
            "lastUpdatedAt": "2023-01-17T18:25:44.552Z"
        }],
        "nextToken": "REDACTED"
    }

For more information, see `Get started with the Trusted Advisor API <https://docs.aws.amazon.com/awssupport/latest/user/get-started-with-aws-trusted-advisor-api.html>`__ in the *AWS Trusted Advisor User Guide*.