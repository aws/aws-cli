**To add a tag to an AWS Direct Connect resource**

The following ``tag-resource`` example adds a tag with a key of ``Name`` and a value of ``VAConnection`` to the connection ``dxcon-abcabc12``. ::

    aws directconnect tag-resource \
        --resource-arn arn:aws:directconnect:us-west-2:123456789012:dxcon/dxcon-abcabc12 \
        --tags "key=Name,value=VAConnection"

This command produces no output.

For more information, see `Tag AWS Direct Connect resources <https://docs.aws.amazon.com/directconnect/latest/UserGuide/using-tags.html>`__ in the *AWS Direct Connect User Guide*.
