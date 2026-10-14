**To list workflows that you own**

The following ``list-workflows`` example lists the workflow versions that your account owns. ::

    aws imagebuilder list-workflows \
        --owner Self

Output::

    {
        "workflowVersionList": [
            {
                "arn": "arn:aws:imagebuilder:us-west-2:123456789012:workflow/build/my-example-build-workflow/1.0.0",
                "name": "my-example-build-workflow",
                "version": "1.0.0",
                "description": "Builds my example image",
                "type": "BUILD",
                "owner": "123456789012",
                "dateCreated": "2026-09-09T19:56:09.033Z"
            },
            {
                "arn": "arn:aws:imagebuilder:us-west-2:123456789012:workflow/test/my-example-test-workflow/1.0.0",
                "name": "my-example-test-workflow",
                "version": "1.0.0",
                "description": "Tests my example image",
                "type": "TEST",
                "owner": "123456789012",
                "dateCreated": "2026-09-09T19:56:12.440Z"
            }
        ]
    }

For more information, see `List image workflows <https://docs.aws.amazon.com/imagebuilder/latest/userguide/list-image-workflows.html>`__ in the *EC2 Image Builder User Guide*.
