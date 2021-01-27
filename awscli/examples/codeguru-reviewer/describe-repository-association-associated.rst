**To return information about a repository association**

The following ``describe-repository-association`` example returns information about a repository association that uses a GitHub Enterprise repository and is in the ``Associated`` state. ::

    aws codeguru-reviewer describe-repository-association \
        --association-arn arn:aws:codeguru-reviewer:us-west-2:123456789012:association:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "RepositoryAssociation": {
            "AssociationId": "b822717e-0711-4e8a-bada-0e738289c75e",
            "Name": "mySampleRepo",
            "LastUpdatedTimeStamp": 1588102637.649,
            "ProviderType": "GitHub",
            "CreatedTimeStamp": 1588102615.636,
            "Owner": "sample-owner",
            "State": "Associated",
            "StateReason": "Pull Request Notification configuration successful",
            "AssociationArn": "arn:aws:codeguru-reviewer:us-west-2:123456789012:association:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
        }
    }

For more information, see `DescribeRepositoryAssociation<https://docs.aws.amazon.com/codeguru/latest/reviewer-api/API_DescribeRepositoryAssociation.html>`__ in the *Amazon DevOps Guru API Reference*