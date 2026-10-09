**To list the build versions of a component**

The following ``list-component-build-versions`` example lists the build versions that exist for version 1.0.0 of the specified component. The ARN that you specify is a component version ARN, with exactly three version nodes and no build number. The list returns the most recent build version first, with the ``changeDescription`` field showing what changed in each build. ::

    aws imagebuilder list-component-build-versions \
        --component-version-arn arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-component/1.0.0

Output::

    {
        "componentSummaryList": [
            {
                "arn": "arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-component/1.0.0/2",
                "name": "my-example-component",
                "version": "1.0.0",
                "platform": "Linux",
                "supportedOsVersions": [
                    "Amazon Linux 2023"
                ],
                "state": {
                    "status": "ACTIVE"
                },
                "type": "BUILD",
                "owner": "123456789012",
                "description": "Installs the latest version of my application",
                "changeDescription": "Updated the install command to use dnf",
                "dateCreated": "2026-09-09T18:35:23.098Z",
                "tags": {
                    "Environment": "Production"
                }
            },
            {
                "arn": "arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-component/1.0.0/1",
                "name": "my-example-component",
                "version": "1.0.0",
                "platform": "Linux",
                "supportedOsVersions": [
                    "Amazon Linux 2023"
                ],
                "state": {
                    "status": "ACTIVE"
                },
                "type": "BUILD",
                "owner": "123456789012",
                "description": "Installs the latest version of my application",
                "changeDescription": "Initial version",
                "dateCreated": "2026-09-09T18:35:20.731Z",
                "tags": {
                    "Environment": "Production"
                }
            }
        ],
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `List and view component details <https://docs.aws.amazon.com/imagebuilder/latest/userguide/component-details.html>`__ in the *EC2 Image Builder User Guide*.
