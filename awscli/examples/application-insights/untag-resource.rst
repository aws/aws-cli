**To remove tags from an application**

This example uses the ``untag-resource`` command to remove one or more tags from an application. ::

    aws application-insights untag-resource \
        --resource-arn arn:aws:applicationinsights:eu-west-1:012345678901:application/resource-group/sameplegroup \
        --tag-keys sample

This command returns to the prompt if successful.