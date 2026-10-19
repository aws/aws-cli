**To list the steps that ran in a workflow execution**

The following ``list-workflow-step-executions`` example lists runtime details for each step in the specified runtime instance of a workflow, in this case the build workflow from an image build. ::

    aws imagebuilder list-workflow-step-executions \
        --workflow-execution-id wf-a1b2c3d4-5678-90ab-cdef-EXAMPLE33333

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "steps": [
            {
                "stepExecutionId": "step-a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "name": "LaunchBuildInstance",
                "action": "LaunchInstance",
                "status": "COMPLETED",
                "inputs": "{\"waitFor\": \"ssmAgent\"}",
                "outputs": "{\"instanceId\": \"i-1234567890abcdef0\"}",
                "startTime": "2026-09-09T19:12:23.418Z",
                "endTime": "2026-09-09T19:14:50.822Z"
            },
            {
                "stepExecutionId": "step-a1b2c3d4-5678-90ab-cdef-EXAMPLE55555",
                "name": "ApplyBuildComponents",
                "action": "ExecuteComponents",
                "status": "SKIPPED",
                "inputs": "{\"instanceId.$\": \"$.stepOutputs.LaunchBuildInstance.instanceId\"}",
                "startTime": "2026-09-09T19:14:51.229Z",
                "endTime": "2026-09-09T19:14:51.229Z"
            },
            {
                "stepExecutionId": "step-a1b2c3d4-5678-90ab-cdef-EXAMPLE88888",
                "name": "InventoryCollection",
                "action": "CollectImageMetadata",
                "status": "COMPLETED",
                "inputs": "{\"instanceId\": \"i-1234567890abcdef0\"}",
                "outputs": "{\"osVersion\": \"Amazon Linux 2023\", \"associationId\": \"a1b2c3d4-5678-90ab-cdef-EXAMPLEaaaaa\"}",
                "startTime": "2026-09-09T19:14:51.818Z",
                "endTime": "2026-09-09T19:16:26.267Z"
            },
            {
                "stepExecutionId": "step-a1b2c3d4-5678-90ab-cdef-EXAMPLE99999",
                "name": "RunSanitizeScript",
                "action": "SanitizeInstance",
                "status": "COMPLETED",
                "outputs": "{\"status\": \"Success\", \"output\": \"Skipping cleanup\\n\", \"runCommandId\": \"a1b2c3d4-5678-90ab-cdef-EXAMPLEbbbbb\"}",
                "startTime": "2026-09-09T19:16:26.742Z",
                "endTime": "2026-09-09T19:16:36.559Z"
            },
            {
                "stepExecutionId": "step-a1b2c3d4-5678-90ab-cdef-EXAMPLE00000",
                "name": "RunSysPrepScript",
                "action": "RunSysPrep",
                "status": "SKIPPED",
                "inputs": "{\"instanceId.$\": \"$.stepOutputs.LaunchBuildInstance.instanceId\"}",
                "startTime": "2026-09-09T19:16:36.973Z",
                "endTime": "2026-09-09T19:16:36.973Z"
            },
            {
                "stepExecutionId": "step-a1b2c3d4-5678-90ab-cdef-EXAMPLE66666",
                "name": "CreateOutputAMI",
                "action": "CreateImage",
                "status": "COMPLETED",
                "inputs": "{\"instanceId\": \"i-1234567890abcdef0\"}",
                "outputs": "{\"imageId\": \"ami-1234567890abcdef0\"}",
                "startTime": "2026-09-09T19:16:37.499Z",
                "endTime": "2026-09-09T19:19:02.135Z"
            },
            {
                "stepExecutionId": "step-a1b2c3d4-5678-90ab-cdef-EXAMPLE77777",
                "name": "TerminateBuildInstance",
                "action": "TerminateInstance",
                "status": "COMPLETED",
                "inputs": "{\"instanceId\": \"i-1234567890abcdef0\"}",
                "startTime": "2026-09-09T19:19:02.546Z",
                "endTime": "2026-09-09T19:19:06.132Z"
            }
        ],
        "workflowBuildVersionArn": "arn:aws:imagebuilder:us-west-2:aws:workflow/build/build-image/1.0.3/1",
        "workflowExecutionId": "wf-a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
        "imageBuildVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-recipe/1.0.0/1"
    }

For more information, see `Manage build, test, and distribution workflows for Image Builder images <https://docs.aws.amazon.com/imagebuilder/latest/userguide/manage-image-workflows.html>`__ in the *EC2 Image Builder User Guide*.
