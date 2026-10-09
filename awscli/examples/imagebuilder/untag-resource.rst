**To remove a tag from a resource**

The following ``untag-resource`` example removes the ``CostCenter`` tag key from the specified component build version. ::

    aws imagebuilder untag-resource \
        --resource-arn arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-tagged-component/1.0.0/1 \
        --tag-keys CostCenter

This command produces no output.

For more information, see `Tag Image Builder output resources <https://docs.aws.amazon.com/imagebuilder/latest/userguide/tag-resources.html>`__ in the *EC2 Image Builder User Guide*.
