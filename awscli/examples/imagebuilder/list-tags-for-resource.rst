**To list tags for a specific resource**

The following ``list-tags-for-resource`` example lists all of the tags for the specified resource. ::

    aws imagebuilder list-tags-for-resource \
        --resource-arn arn:aws:imagebuilder:us-west-2:123456789012:image-pipeline/mywindows2016pipeline

Output::

    {
        "tags": {
            "KeyName": "KeyValue"
        }
    }
