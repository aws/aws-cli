**To remove a tag from a resource**

The following ``untag-resource`` example removes the ``department`` tag from a workflow. ::

    aws omics untag-resource \
        --resource-arn arn:aws:omics:us-west-2:123456789012:workflow/1234567 \
        --tag-keys department

For more information, see `Removing tags from a data store <https://docs.aws.amazon.com/omics/latest/dev/remove-tags.html>`__ in the *AWS HealthOmics User Guide*.
