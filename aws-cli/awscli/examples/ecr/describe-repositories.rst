**To describe the repositories in a registry**

The following ``describe-repositories`` example describes the repositories in the default registry for an account. ::

    aws ecr describe-repositories

Output::

    {
        "repositories": [
            {
                "registryId": "123456789012",
                "repositoryName": "ubuntu",
                "repositoryArn": "arn:aws:ecr:us-west-2:123456789012:repository/ubuntu"
            },
            {
                "registryId": "123456789012",
                "repositoryName": "test",
                "repositoryArn": "arn:aws:ecr:us-west-2:123456789012:repository/test"
            }
        ]
    }

For more information, see `Viewing the contents and details of a private repository in Amazon ECR <https://docs.aws.amazon.com/AmazonECR/latest/userguide/repository-info.html>`__ in the *Amazon ECR User Guide*.
