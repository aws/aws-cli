**To return information about a repository association**

The following ``describe-repository-association`` example returns information about a repository association that uses a GitHub Enterprise repository and is in the ``Failed`` state. ::

    aws codeguru-reviewer describe-repository-association \
        --association-arn arn:aws:codeguru-reviewer:us-west-2:123456789012:association:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "RepositoryAssociation": {
            "ProviderType": "GitHubEnterpriseServer",
            "Name": "mySampleRepo",
            "LastUpdatedTimeStamp": 1596217036.892,
            "AssociationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "CreatedTimeStamp": 1596216896.979,
            "ConnectionArn": "arn:aws:codestar-connections:us-west-2:123456789012:connection/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "State": "Failed",
            "StateReason": "Failed, Please retry.",
            "AssociationArn": "arn:aws:codeguru-reviewer:us-west-2:123456789012:association:a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
            "Owner": "sample-owner"
        }
    }

For more information, see `DescribeRepositoryAssociation<https://docs.aws.amazon.com/codeguru/latest/reviewer-api/API_DescribeRepositoryAssociation.html>`__ in the *Amazon DevOps Guru API Reference*.