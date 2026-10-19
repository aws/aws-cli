**To get the details of a component build version**

The following ``get-component`` example retrieves the details of a component build version. The ``data`` field in the response contains the YAML document that defines the component, decrypted for the component owner. ::

    aws imagebuilder get-component \
        --component-build-version-arn arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-component/1.0.0/1

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "component": {
            "arn": "arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-component/1.0.0/1",
            "name": "my-example-component",
            "version": "1.0.0",
            "description": "Installs the latest version of my application",
            "changeDescription": "Initial version",
            "type": "BUILD",
            "platform": "Linux",
            "state": {
                "status": "ACTIVE"
            },
            "owner": "123456789012",
            "data": "name: InstallMyApp\ndescription: Installs my application\nschemaVersion: 1.0\nphases:\n  - name: build\n    steps:\n      - name: InstallApp\n        action: ExecuteBash\n        inputs:\n          commands:\n            - sudo yum -y install my-app\n",
            "encrypted": true,
            "dateCreated": "2026-09-09T18:31:30.404Z",
            "tags": {}
        },
        "latestVersionReferences": {
            "latestVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-component/x.x.x",
            "latestMajorVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-component/1.x.x",
            "latestMinorVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-component/1.0.x",
            "latestPatchVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-component/1.0.0"
        }
    }

For more information, see `List and view component details <https://docs.aws.amazon.com/imagebuilder/latest/userguide/component-details.html>`__ in the *EC2 Image Builder User Guide*.
