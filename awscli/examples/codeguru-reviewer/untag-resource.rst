**To untag an associated repository**

The following ``untag-resource`` removes two tags with keys "Secret" and "Team" from an associated repository. ::

    aws codeguru-reviewer untag-resource \
        --resource-arn arn:aws:codeguru-reviewer:us-west-2:123456789012:association:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --tag-keys Status Team

This command produces no output.

For more information, see `UntagResource<https://docs.aws.amazon.com/codeguru/latest/reviewer-api/API_UntagResource.html>`__ in the *Amazon CodeGuru Reviewer API Reference*.