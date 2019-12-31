**To view a list of Contributor Insights summaries**

The following ``list-contributor-insights`` example displays a list of Contributor Insights summaries. ::

    aws dynamodb list-contributor-insights

Output::

    {
        "ContributorInsightsSummaries": [
            {
                "TableName": "MusicCollection",
                "ContributorInsightsStatus": "ENABLED"
            }
        ]
    }

For more information, see `Analyzing Data Access Using CloudWatch Contributor Insights for DynamoDB <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/contributorinsights.html>`__ in the *Amazon DynamoDB Developer Guide*.
