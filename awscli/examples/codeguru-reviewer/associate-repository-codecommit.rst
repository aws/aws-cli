**To create an AWS CodeCommit repository association**

The following ``associate-repository`` example creates a respository association using an existing AWS CodeCommit repository. ::

    aws codeguru-reviewer associate-repository \
        --repository CodeCommit={Name=mySampleRepo}

Output::

    {
        "RepositoryAssociation": {
            "AssociationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "Name": "My-ecs-beta-repo",
            "LastUpdatedTimeStamp": 1595634764.029,
            "ProviderType": "CodeCommit",
            "CreatedTimeStamp": 1595634764.029,
            "Owner": "544120495673",
            "State": "Associating",
            "StateReason": "Pending Repository Association",
            "AssociationArn": "arn:aws:codeguru-reviewer:us-west-2:544120495673:association:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
        }
    }

For more information, see `AssociateRepository<https://docs.aws.amazon.com/codeguru/latest/reviewer-api/API_AssociateRepository.html>`__ in the *Amazon DevOps Guru API Reference*