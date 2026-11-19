**To list the resources that a lifecycle execution acted on**

The following ``list-lifecycle-execution-resources`` example lists the resources that the specified lifecycle execution acted on. For a scheduled resource state update that hasn't started to apply changes yet, the resources list is empty. ::

    aws imagebuilder list-lifecycle-execution-resources \
        --lifecycle-execution-id lce-a1b2c3d4-5678-90ab-cdef-EXAMPLE33333

Output::

    {
        "resources": [],
        "lifecycleExecutionId": "lce-a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
        "lifecycleExecutionState": {
            "status": "IN_PROGRESS"
        }
    }

For more information, see `How lifecycle policy execution works <https://docs.aws.amazon.com/imagebuilder/latest/userguide/lifecycle-policy-execution.html>`__ in the *EC2 Image Builder User Guide*.
