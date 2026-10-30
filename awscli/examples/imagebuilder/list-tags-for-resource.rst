**To list tags for a specific resource**

The following ``list-tags-for-resource`` example lists all of the tags for a specific resource. ::

    aws imagebuilder list-tags-for-resource \
        --resource-arn arn:aws:imagebuilder:us-west-2:123456789012:image-pipeline/mywindows2016pipeline

Output::

    {
        "tags": {
            "KeyName": "KeyValue"
        }
    }

For more information, see `Manage custom image creation in Image Builder through a repeatable pipeline process <https://docs.aws.amazon.com/imagebuilder/latest/userguide/manage-pipelines.html>`__ in the *EC2 Image Builder Users Guide*.
