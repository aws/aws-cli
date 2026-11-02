**To get a list of all tag keys**

The following ``get-tag-keys`` example retrieves the list of all tag key names used by resources in the account. ::

    aws resourcegroupstaggingapi get-tag-keys

Output::

    {
        "TagKeys": [
            "Environment",
            "CostCenter",
            "Department"
        ]
    }

For more information, see `What is Tag Editor? <https://docs.aws.amazon.com/tag-editor/latest/userguide/tagging.html>`__ in the *Tagging AWS Resources and Tag Editor User Guide*.

