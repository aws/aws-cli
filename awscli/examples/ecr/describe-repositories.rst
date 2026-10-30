**To describe the repositories in a registry**

The following ``describe-repositories`` example describes the repositories in the default registry for an account. ::

    aws ecr describe-repositories

Output::

    {
        "repositories": [
            {
                "registryId": "012345678910",
                "repositoryName": "ubuntu",
                "repositoryArn": "arn:aws:ecr:us-west-2:012345678910:repository/ubuntu"
            },
            {
                "registryId": "012345678910",
                "repositoryName": "test",
                "repositoryArn": "arn:aws:ecr:us-west-2:012345678910:repository/test"
            }
        ]
    }
