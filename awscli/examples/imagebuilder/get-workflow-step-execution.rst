**To get the runtime details of a workflow step**

The following ``get-workflow-step-execution`` example retrieves runtime details for the step that launched the build instance during an image build, with the step's input parameters and output values returned as JSON-encoded strings. ::

    aws imagebuilder get-workflow-step-execution \
        --step-execution-id step-a1b2c3d4-5678-90ab-cdef-EXAMPLE33333

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "stepExecutionId": "step-a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
        "workflowBuildVersionArn": "arn:aws:imagebuilder:us-west-2:aws:workflow/build/build-image/1.0.3/1",
        "workflowExecutionId": "wf-a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
        "imageBuildVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-recipe/1.0.0/1",
        "name": "LaunchBuildInstance",
        "action": "LaunchInstance",
        "status": "COMPLETED",
        "inputs": "{\"waitFor\": \"ssmAgent\"}",
        "outputs": "{\"instanceId\": \"i-1234567890abcdef0\"}",
        "startTime": "2026-09-09T19:12:23.418Z",
        "endTime": "2026-09-09T19:14:50.822Z",
        "onFailure": "Abort",
        "timeoutSeconds": 4500
    }

For more information, see `Manage build, test, and distribution workflows for Image Builder images <https://docs.aws.amazon.com/imagebuilder/latest/userguide/manage-image-workflows.html>`__ in the *EC2 Image Builder User Guide*.
