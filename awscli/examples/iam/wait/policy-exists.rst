**To pause running until the specified role exists**

The following ``wait policy-exists`` example pauses and continues only after it can confirm that the specified policy exists. ::

    aws iam wait policy-exists \
        --policy-arn arn:aws:iam::123456789012:policy/MyPolicy

This command produces no output.

For more information, see `Managed policies and inline policies <https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_managed-vs-inline.html>`__ in the *AWS IAM User Guide*.
