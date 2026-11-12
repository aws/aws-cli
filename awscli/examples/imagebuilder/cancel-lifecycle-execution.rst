**To cancel a lifecycle execution**

The following ``cancel-lifecycle-execution`` example cancels the scheduled resource state update associated with the specified lifecycle execution ID before it runs. ::

    aws imagebuilder cancel-lifecycle-execution \
        --lifecycle-execution-id lce-a1b2c3d4-5678-90ab-cdef-EXAMPLE33333 \
        --client-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "lifecycleExecutionId": "lce-a1b2c3d4-5678-90ab-cdef-EXAMPLE33333"
    }

For more information, see `How lifecycle policy execution works <https://docs.aws.amazon.com/imagebuilder/latest/userguide/lifecycle-policy-execution.html>`__ in the *EC2 Image Builder User Guide*.
