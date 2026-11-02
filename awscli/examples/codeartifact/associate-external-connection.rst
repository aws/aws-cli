**To add an external connection to a repository**

The following ``associate-external-connection`` example adds an external connection to npmjs.com to a repository named test-repo. ::

    aws codeartifact associate-external-connection \
        --repository test-repo \
        --domain test-domain \
        --external-connection public:npmjs

Output::

    {
        "repository": {
            "name": "test-repo",
            "administratorAccount": "123456789012",
            "domainName": "test-domain",
            "domainOwner": "123456789012",
            "arn": "arn:aws:codeartifact:us-west-2:123456789012:repository/test-domain/test-repo",
            "upstreams": [],
            "externalConnections": [
                {
                    "externalConnectionName": "public:npmjs",
                    "packageFormat": "npm",
                    "status": "AVAILABLE"
                }
            ]
        }
    }

For more information, see `Add an external connection <https://docs.aws.amazon.com/codeartifact/latest/ug/external-connection.html>`__ in the *AWS CodeArtifact User Guide*.