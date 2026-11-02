**To remove a tag from an AWS Direct Connect resource**

The following ``untag-resource`` example removes the tag with the key ``Name`` from connection ``dxcon-abcabc12``. ::

    aws directconnect untag-resource \
        --resource-arn arn:aws:directconnect:us-west-2:123456789012:dxcon/dxcon-abcabc12 \
        --tag-keys Name

This command produces no output.

For more information, see `Tag AWS Direct Connect resources <https://docs.aws.amazon.com/directconnect/latest/UserGuide/using-tags.html>`__ in the *AWS Direct Connect User Guide*.
