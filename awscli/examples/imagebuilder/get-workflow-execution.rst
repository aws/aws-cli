**To get the runtime details for a workflow execution**

The following ``get-workflow-execution`` example retrieves runtime status and step counts for the build workflow that ran for an image build version, using the workflow execution ID that ``list-workflow-executions`` returns. ::

    aws imagebuilder get-workflow-execution \
        --workflow-execution-id wf-a1b2c3d4-5678-90ab-cdef-EXAMPLE33333

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "workflowBuildVersionArn": "arn:aws:imagebuilder:us-west-2:aws:workflow/build/build-image/1.0.3/1",
        "workflowExecutionId": "wf-a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
        "imageBuildVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-recipe/1.0.0/1",
        "type": "BUILD",
        "status": "COMPLETED",
        "totalStepCount": 7,
        "totalStepsSucceeded": 5,
        "totalStepsFailed": 0,
        "totalStepsSkipped": 2,
        "startTime": "2026-09-09T19:12:23.175Z",
        "endTime": "2026-09-09T19:19:06.158Z"
    }

For more information, see `Manage build, test, and distribution workflows for Image Builder images <https://docs.aws.amazon.com/imagebuilder/latest/userguide/manage-image-workflows.html>`__ in the *EC2 Image Builder User Guide*.
