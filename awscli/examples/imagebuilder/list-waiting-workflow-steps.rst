**To list workflow steps that are waiting for an action**

The following ``list-waiting-workflow-steps`` example lists the workflow steps in your account that are paused at a ``WaitForAction`` step, waiting for you to resume or stop the workflow with ``send-workflow-step-action``. ::

    aws imagebuilder list-waiting-workflow-steps \
        --max-results 25

Output::

    {
        "steps": [
            {
                "stepExecutionId": "step-a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "imageBuildVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-wait-recipe/1.0.0/1",
                "workflowExecutionId": "wf-a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "workflowBuildVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:workflow/build/my-example-wait-workflow/1.0.0/1",
                "name": "WaitForApproval",
                "action": "WaitForAction",
                "startTime": "2026-09-09T20:02:59.931Z"
            }
        ]
    }

For more information, see `Supported step actions for your workflow document <https://docs.aws.amazon.com/imagebuilder/latest/userguide/wfdoc-step-actions.html>`__ in the *EC2 Image Builder User Guide*.
