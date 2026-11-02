**To list tags for an accelerator**

The following ``list-tags-for-resource`` example lists the tags for a specific accelerator. ::

    aws globalaccelerator list-tags-for-resource \
        --resource-arn arn:aws:globalaccelerator::123456789012:accelerator/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "Tags": [
            {
                "Key": "Project",
                "Value": "A123456"
            }
        ]
    }

For more information, see `Tagging in AWS Global Accelerator <https://docs.aws.amazon.com/global-accelerator/latest/dg/tagging-in-global-accelerator.html>`__ in the *AWS Global Accelerator Developer Guide*.
