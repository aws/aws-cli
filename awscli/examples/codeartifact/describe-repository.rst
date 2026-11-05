**To get information about a repository**

The following ``describe-repository`` example returns a RepositoryDescription object for a repository named test-repo. ::

    aws codeartifact describe-repository \
        --domain test-domain \
        --repository test-repo

Output::

    {
        "repository": {
            "name": "test-repo",
            "administratorAccount": "123456789012",
            "domainName": "test-domain",
            "domainOwner": "123456789012",
            "arn": "arn:aws:codeartifact:us-west-2:123456789012:repository/test-domain/test-repo",
            "description": "This is a test repository.",
            "upstreams": [],
            "externalConnections": []
        }
    }

For more information, see `Create a domain <https://docs.aws.amazon.com/codeartifact/latest/ug/create-repo.html>`__ in the *AWS CodeArtifact User Guide*.