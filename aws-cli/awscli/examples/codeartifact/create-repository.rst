**To create a repository**

The following ``create-repository`` example creates a repository named test-repo inside a domain named test-domain. ::

    aws codeartifact create-repository \
        --domain test-domain \
        --domain-owner 123456789012 \
        --repository test-repo \
        --description "This is a test repository."

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