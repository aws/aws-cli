**To stop a workflow step that is waiting for an action**

The following ``send-workflow-step-action`` example sends the ``STOP`` action to a workflow step that has paused the image build, identified by the step execution ID that ``list-waiting-workflow-steps`` returns. This stops the image build. ::

    aws imagebuilder send-workflow-step-action \
        --step-execution-id step-a1b2c3d4-5678-90ab-cdef-EXAMPLE33333 \
        --image-build-version-arn arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-wait-recipe/1.0.0/1 \
        --action STOP \
        --client-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "stepExecutionId": "step-a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
        "imageBuildVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-wait-recipe/1.0.0/1",
        "clientToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
    }

For more information, see `Supported step actions for your workflow document <https://docs.aws.amazon.com/imagebuilder/latest/userguide/wfdoc-step-actions.html>`__ in the *EC2 Image Builder User Guide*.
