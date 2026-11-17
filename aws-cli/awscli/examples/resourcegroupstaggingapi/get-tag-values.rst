**To get a list of all tag values**

The following ``get-tag-values`` example displays all of the values used for the specified key for all resources in the current AWS Region. ::

    aws resourcegroupstaggingapi get-tag-values \
        --key=Environment

Output::

    {
        "TagValues": [
            "Alpha",
            "Gamma",
            "Production"
        ]
    }

For more information, see `What is Tag Editor? <https://docs.aws.amazon.com/tag-editor/latest/userguide/tagging.html>`__ in the *Tagging AWS Resources and Tag Editor User Guide*.
