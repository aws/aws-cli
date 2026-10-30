**To tag a Resource Explorer view**

The following ``tag-resource`` example adds the tag key "environment" with the value "production" to the view with the specified ARN. ::

    aws resource-explorer-2 tag-resource \
        --resource-arn arn:aws:resource-explorer-2:us-west-2:123456789012:view/My-View//a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --tags environment=production

This command produces no output.

For more information, see `Adding tags to views <https://docs.aws.amazon.com/resource-explorer/latest/userguide/configure-views-tag.html>`__ in the *AWS Resource Explorer Users Guide*.