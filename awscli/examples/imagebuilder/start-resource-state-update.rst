**To schedule an image build version for deprecation**

The following ``start-resource-state-update`` example schedules the specified image build version and its AMI to move to the DEPRECATED state at the requested future time. It returns the ID of the lifecycle execution that applies the update. ::

    aws imagebuilder start-resource-state-update \
        --resource-arn arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-recipe/1.0.0/1 \
        --state '{"status": "DEPRECATED"}' \
        --execution-role arn:aws:iam::123456789012:role/my-example-state-update-role \
        --include-resources '{"amis": true}' \
        --update-at 2026-09-11T21:20:00Z \
        --client-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "lifecycleExecutionId": "lce-a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
        "resourceArn": "arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-recipe/1.0.0/1"
    }

For more information, see `Manage lifecycle policies for Image Builder images <https://docs.aws.amazon.com/imagebuilder/latest/userguide/manage-image-lifecycles.html>`__ in the *EC2 Image Builder User Guide*.
