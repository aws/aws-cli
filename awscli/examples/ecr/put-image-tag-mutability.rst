**To make a repository's image tags immutable**

The following ``put-image-tag-mutability`` example sets immutable image tags on the ``hello-world`` repository. ::

    aws ecr put-image-tag-mutability \
        --repository-name hello-world \
        --image-tag-mutability IMMUTABLE

Output::

    {
        "registryId": "012345678910",
        "repositoryName": "hello-world",
        "imageTagMutability": "IMMUTABLE"
    }
