**To remove tags from an existing resource**

The following ``untag-resource`` example removes the specified tags from an existing subscriber resource. ::

    aws securitylake untag-resource \
        --resource-arn "arn:aws:securitylake:us-west-2:123456789012:subscriber/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --tag-keys Environment Owner

This command produces no output.

For more information, see `Tagging Amazon Security Lake resources <https://docs.aws.amazon.com/security-lake/latest/userguide/tagging-resources.html>`__ in the *Amazon Security Lake User Guide*.
