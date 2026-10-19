**To add tags to a component**

The following ``tag-resource`` example adds two tags to a component build version. ::

    aws imagebuilder tag-resource \
        --resource-arn arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-tagged-component/1.0.0/1 \
        --tags Environment=Production,CostCenter=12345

This command produces no output.

For more information, see `Tag Image Builder output resources <https://docs.aws.amazon.com/imagebuilder/latest/userguide/tag-resources.html>`__ in the *EC2 Image Builder User Guide*.
