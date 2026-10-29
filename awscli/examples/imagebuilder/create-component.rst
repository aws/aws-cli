**To create a component**

The following ``create-component`` example creates a component that uses a JSON document file and references a component document in YAML format that is uploaded to an Amazon S3 bucket. ::

    aws imagebuilder create-component \
        --cli-input-json file://create-component.json

Contents of ``create-component.json``::

    {
        "name": "MyExampleComponent",
        "semanticVersion": "2019.12.02",
        "description": "An example component that builds, validates and tests an image",
        "changeDescription": "Initial version.",
        "platform": "Windows",
        "uri": "s3://amzn-s3-demo-bucket/s3-bucket-path/component.yaml"
    }

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "clientToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "componentBuildVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:component/examplecomponent/2019.12.02/1"
    }

For more information, see `Manage custom image creation in Image Builder through a repeatable pipeline process <https://docs.aws.amazon.com/imagebuilder/latest/userguide/manage-pipelines.html>`__ in the *EC2 Image Builder Users Guide*.
