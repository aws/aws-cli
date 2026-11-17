**To get the policies for a resource**

The following ``get-resource-policies`` example displays the resource-based permission policies for the specified resource associated with a resource share. ::

    aws ram get-resource-policies \
        --resource-arns arn:aws:ec2:us-west-2:123456789012:subnet/subnet-0250c25a1fEXAMPLE

Output::

    {
        "policies": [
            "{\"Version\":\"2008-10-17\",\"Statement\":[{\"Sid\":\"RamStatement1\",\"Effect\":\"Allow\",\"Principal\":{\"AWS\":[]},\"Action\":[\"ec2:RunInstances\",\"ec2:CreateNetworkInterface\",\"ec2:DescribeSubnets\"],\"Resource\":\"arn:aws:ec2:us-west-2:123456789012:subnet/subnet-0250c25a1fEXAMPLE\"}]}"
        ]
    }

For more information, see `Viewing resource shares you created in AWS RAM <https://docs.aws.amazon.com/ram/latest/userguide/working-with-sharing-view-rs.html>`__ in the *AWS RAM User Guide*.
