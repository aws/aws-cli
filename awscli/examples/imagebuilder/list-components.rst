**To list the components that you own**

The following ``list-components`` example lists the component versions that your account owns, filtered to components for the Linux platform. ::

    aws imagebuilder list-components \
        --owner Self \
        --filters name=platform,values=Linux

Output::

    {
        "componentVersionList": [
            {
                "arn": "arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-component/1.0.0",
                "name": "my-example-component",
                "version": "1.0.0",
                "description": "Installs my example application",
                "platform": "Linux",
                "supportedOsVersions": [
                    "Amazon Linux 2023"
                ],
                "type": "BUILD",
                "owner": "123456789012",
                "dateCreated": "2026-09-09T18:31:49.661Z",
                "status": "ACTIVE"
            },
            {
                "arn": "arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-imported-component/1.0.0",
                "name": "my-example-imported-component",
                "version": "1.0.0",
                "description": "Installs my application from an imported shell script",
                "platform": "Linux",
                "type": "BUILD",
                "owner": "123456789012",
                "dateCreated": "2026-09-09T18:31:21.941Z",
                "status": "ACTIVE"
            },
            {
                "arn": "arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-test-component/1.0.0",
                "name": "my-example-test-component",
                "version": "1.0.0",
                "description": "Verifies that my example application is installed",
                "platform": "Linux",
                "type": "TEST",
                "owner": "123456789012",
                "dateCreated": "2026-09-09T18:31:52.888Z",
                "status": "ACTIVE"
            }
        ],
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `List and view component details <https://docs.aws.amazon.com/imagebuilder/latest/userguide/component-details.html>`__ in the *EC2 Image Builder User Guide*.
