**To list lifecycle executions for an image build version**

The following ``list-lifecycle-executions`` example lists the lifecycle executions that have run against the specified image build version. The execution shown was started with ``start-resource-state-update`` rather than a lifecycle policy, so it has no ``lifecyclePolicyArn``. ::

    aws imagebuilder list-lifecycle-executions \
        --resource-arn arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-recipe/1.0.0/1

Output::

    {
        "lifecycleExecutions": [
            {
                "lifecycleExecutionId": "lce-a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "resourcesImpactedSummary": {
                    "hasImpactedResources": false
                },
                "state": {
                    "status": "IN_PROGRESS"
                },
                "startTime": "2026-09-09T21:42:29.801000+00:00"
            }
        ]
    }

For more information, see `How lifecycle policy execution works <https://docs.aws.amazon.com/imagebuilder/latest/userguide/lifecycle-policy-execution.html>`__ in the *EC2 Image Builder User Guide*.
