**To list the workflow runtime instances for an image build version**

The following ``list-workflow-executions`` example lists the workflow runtime instances that ran for the specified image build version, which was built with the Image Builder default build and test workflows. ::

    aws imagebuilder list-workflow-executions \
        --image-build-version-arn arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-recipe/1.0.0/1

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "workflowExecutions": [
            {
                "workflowBuildVersionArn": "arn:aws:imagebuilder:us-west-2:aws:workflow/build/build-image/1.0.3/1",
                "workflowExecutionId": "wf-a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "type": "BUILD",
                "status": "COMPLETED",
                "totalStepCount": 7,
                "totalStepsSucceeded": 5,
                "totalStepsFailed": 0,
                "totalStepsSkipped": 2,
                "startTime": "2026-09-09T19:12:23.175Z",
                "endTime": "2026-09-09T19:19:06.158Z",
                "retried": false
            },
            {
                "workflowBuildVersionArn": "arn:aws:imagebuilder:us-west-2:aws:workflow/test/test-image/1.0.3/1",
                "workflowExecutionId": "wf-a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "type": "TEST",
                "status": "COMPLETED",
                "totalStepCount": 4,
                "totalStepsSucceeded": 2,
                "totalStepsFailed": 0,
                "totalStepsSkipped": 2,
                "startTime": "2026-09-09T19:19:11.709Z",
                "endTime": "2026-09-09T19:21:47.830Z",
                "retried": false
            }
        ],
        "imageBuildVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-recipe/1.0.0/1"
    }

For more information, see `Manage build, test, and distribution workflows for Image Builder images <https://docs.aws.amazon.com/imagebuilder/latest/userguide/manage-image-workflows.html>`__ in the *EC2 Image Builder User Guide*.
