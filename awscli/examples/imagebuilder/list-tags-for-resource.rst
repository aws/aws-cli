**To list the tags for a resource**

The following ``list-tags-for-resource`` example lists the tags that are assigned to an existing component build version. ::

    aws imagebuilder list-tags-for-resource \
        --resource-arn arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-component/1.0.0/1

Output::

    {
        "tags": {
            "CostCenter": "12345",
            "Environment": "Production"
        }
    }

For more information, see `Tag Image Builder output resources <https://docs.aws.amazon.com/imagebuilder/latest/userguide/tag-resources.html>`__ in the *EC2 Image Builder User Guide*.
