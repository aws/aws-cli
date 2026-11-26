**To get the details of a lifecycle execution**

The following ``get-lifecycle-execution`` example retrieves the runtime status of the specified lifecycle execution. If the execution was started by ``start-resource-state-update`` rather than a lifecycle policy run, the response doesn't include the ``lifecyclePolicyArn`` field. ::

    aws imagebuilder get-lifecycle-execution \
        --lifecycle-execution-id lce-a1b2c3d4-5678-90ab-cdef-EXAMPLE33333

Output::

    {
        "lifecycleExecution": {
            "lifecycleExecutionId": "lce-a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
            "resourcesImpactedSummary": {
                "hasImpactedResources": false
            },
            "state": {
                "status": "IN_PROGRESS"
            },
            "startTime": "2026-09-09T21:42:29.801000+00:00"
        }
    }

For more information, see `How lifecycle policy execution works <https://docs.aws.amazon.com/imagebuilder/latest/userguide/lifecycle-policy-execution.html>`__ in the *EC2 Image Builder User Guide*.
