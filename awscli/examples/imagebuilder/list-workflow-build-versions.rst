**To list the build versions of a workflow**

The following ``list-workflow-build-versions`` example lists the build versions that exist for version 1.0.0 of the specified workflow, with the most recent build version first and the change description for each build version showing what changed. ::

    aws imagebuilder list-workflow-build-versions \
        --workflow-version-arn arn:aws:imagebuilder:us-west-2:123456789012:workflow/build/my-example-workflow/1.0.0

Output::

    {
        "workflowSummaryList": [
            {
                "arn": "arn:aws:imagebuilder:us-west-2:123456789012:workflow/build/my-example-workflow/1.0.0/2",
                "name": "my-example-workflow",
                "version": "1.0.0",
                "description": "Workflow to build my example image",
                "changeDescription": "Added a step to collect image metadata from the build instance",
                "type": "BUILD",
                "owner": "123456789012",
                "dateCreated": "2026-09-09T19:56:38.339Z"
            },
            {
                "arn": "arn:aws:imagebuilder:us-west-2:123456789012:workflow/build/my-example-workflow/1.0.0/1",
                "name": "my-example-workflow",
                "version": "1.0.0",
                "description": "Workflow to build my example image",
                "changeDescription": "Initial version",
                "type": "BUILD",
                "owner": "123456789012",
                "dateCreated": "2026-09-09T19:56:35.992Z"
            }
        ]
    }

For more information, see `List image workflows <https://docs.aws.amazon.com/imagebuilder/latest/userguide/list-image-workflows.html>`__ in the *EC2 Image Builder User Guide*.
