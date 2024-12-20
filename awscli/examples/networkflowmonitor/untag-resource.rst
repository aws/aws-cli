**To remove a tag to the specified resource**

The following ``untag-resource`` example removes a tag to the monitor in the specified account. ::

    aws networkflowmonitor untag-resource \
        --resource-arn arn:aws:networkflowmonitor:us-east-1:123456789012:monitor/Demo \
        --tag-keys stack  

This command produces no output.