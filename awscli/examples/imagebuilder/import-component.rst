**To import a component**

The following ``import-component`` example imports a preexisting script using a JSON file. ::

    aws imagebuilder import-component \
        --cli-input-json file://import-component.json

Contents of ``import-component.json``::

    {
        "name": "MyImportedComponent",
        "semanticVersion": "1.0.0",
        "description": "An example of how to import a component",
        "changeDescription": "First commit message.",
        "format": "SHELL",
        "platform": "Windows",
        "type": "BUILD",
        "uri": "s3://amzn-s3-demo-bucket/s3-bucket-path/component.yaml"
    }

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "clientToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "componentBuildVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:component/myimportedcomponent/1.0.0/1"
    }

For more information, see `Manage custom image creation in Image Builder through a repeatable pipeline process <https://docs.aws.amazon.com/imagebuilder/latest/userguide/manage-pipelines.html>`__ in the *EC2 Image Builder Users Guide*.
