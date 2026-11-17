**To list resources from a resource scan**

The following ``list-resource-scan-resources`` example lists resources from the specified resource scan, filtered by resource identifier. ::

    aws cloudformation list-resource-scan-resources \
        --resource-scan-id arn:aws:cloudformation:us-west-2:123456789012:resourceScan/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --resource-identifier MyApp

Output::

    {
        "Resources": [
            {
                "ResourceType": "AWS::EKS::Cluster",
                "ResourceIdentifier": {
                    "ClusterName": "MyAppClusterName"
                },
                "ManagedByStack": false
            },
            {
                "ResourceType": "AWS::AutoScaling::AutoScalingGroup",
                "ResourceIdentifier": {
                    "AutoScalingGroupName": "MyAppASGName"
                },
                "ManagedByStack": false
            }
        ]
    }

For more information, see `Create a CloudFormation template from resources scanned with IaC generator <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/iac-generator-create-template-from-scanned-resources.html>`__ in the *AWS CloudFormation User Guide*.
