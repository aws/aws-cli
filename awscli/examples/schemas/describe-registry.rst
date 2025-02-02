**To describe a specific registry**

The following ``describe-registry`` example describes a specific registry. ::

    aws schemas describe-registry \
        --registry-name example-registry

Output::

    {
        "RegistryArn": "arn:aws:schemas:us-east-1:012345678912:registry/example-registry",
        "RegistryName": "example-registry",
        "Tags": {}
    }

For more information, see `Amazon EventBridge schemas <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html>`__ in the *Amazon EventBridge User Guide*.