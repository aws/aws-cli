**To create a GitHub Enterprise repository association**

The following ``associate-repository`` example creates a respository association using an existing GitHub Enterprise repository. ::

    aws codeguru-reviewer associate-repository \
        --repository 'GitHubEnterpriseServer={Owner=sample-owner, Name=mySampleRepo, ConnectionArn=arn:aws:codestar-connections:us-west-2:123456789012:connection/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 }'

Output::

    {        "RepositoryAssociation": {            "ProviderType": "GitHubEnterpriseServer",            "Name": "mySampleRepo",            "LastUpdatedTimeStamp": 1596216896.979,            "AssociationId": "association:a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",            "CreatedTimeStamp": 1596216896.979,            "ConnectionArn": "arn:aws:codestar-connections:us-west-2:123456789012:connection/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",            "State": "Associating",            "StateReason": "Pending Repository Association",            "AssociationArn": "arn:aws:codeguru-reviewer:us-west-2:123456789012:association:a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",            "Owner": "sample-owner"        }    }

For more information, see `AssociateRepository<https://docs.aws.amazon.com/codeguru/latest/reviewer-api/API_AssociateRepository.html>`__ in the *Amazon DevOps Guru API Reference*
