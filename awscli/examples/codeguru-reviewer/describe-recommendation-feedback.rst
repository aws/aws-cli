**To view information about feedback on a recommendation**

The following ``describe-recommendation-feedback`` displays information about feedback on a recommendation. This recommendation has one ``ThumbsUp`` reaction. ::

    aws codeguru-reviewer describe-recommendation-feedback \
        --code-review-arn arn:aws:codeguru-reviewer:us-west-2:123456789012:association:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111:code-review:RepositoryAnalysis-my-repository-name-branch-abcdefgh12345678 \
        --recommendation-id 3be1b2e5d7ef6e298a06499379ee290c9c596cf688fdcadb08285ddb0dd390eb

Output::

    {
        "RecommendationFeedback": {
            "CodeReviewArn": "arn:aws:codeguru-reviewer:us-west-2:123456789012:association:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111:code-review:RepositoryAnalysis-my-repository-name-branch-abcdefgh12345678",
            "RecommendationId": "3be1b2e5d7ef6e298a06499379ee290c9c596cf688fdcadb08285ddb0dd390eb",
            "Reactions": [
                "ThumbsUp"
            ],
            "UserId": "aws-user-id",
            "CreatedTimeStamp": 1618877070.313,
            "LastUpdatedTimeStamp": 1618877948.881
        }
    }

For more information, see `DescribeRecommendationFeedback <https://docs.aws.amazon.com/codeguru/latest/reviewer-api/API_DescribeRecommendationFeedback.html>`__ in the *Amazon CodeGuru Reviewer API Reference*.