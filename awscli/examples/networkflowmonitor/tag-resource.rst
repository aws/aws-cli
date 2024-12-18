**To add a tag to the specified resource**

The following ``tag-resource`` example adds a tag to the monitor in the specified account. ::

    aws networkflowmonitor tag-resource \
        --resource-arn arn:aws:networkflowmonitor:us-east-1:123456789012:monitor/Demo \
        --tags Key=stack,Value=Production  

This command produces no output.
