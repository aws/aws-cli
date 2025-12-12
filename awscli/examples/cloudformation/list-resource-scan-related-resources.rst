**To list related resources from a resource scan**

The following ``list-resource-scan-related-resources`` example lists resources from the specified resource scan that are related to resources in ``resources.json``. ::

    aws cloudformation list-resource-scan-related-resources \
        --resource-scan-id arn:aws:cloudformation:us-east-1:123456789012:resourceScan/0a699f15-489c-43ca-a3ef-3e6ecfa5da60 \
        --resources file://resources.json

Contents of ``resources.json``::

    [
        {
            "ResourceType": "AWS::EKS::Cluster",
            "ResourceIdentifier": {
                "ClusterName": "MyAppClusterName"
            }
        },
        {
            "ResourceType": "AWS::AutoScaling::AutoScalingGroup",
            "ResourceIdentifier": {
                "AutoScalingGroupName": "MyAppASGName"
            }
        }
    ]

Output::

    {
        "RelatedResources": [
            {
                "ResourceType": "AWS::EKS::Nodegroup",
                "ResourceIdentifier": {
                    "NodegroupName": "MyAppNodegroupName"
                },
                "ManagedByStack": false
            },
            {
                "ResourceType": "AWS::IAM::Role",
                "ResourceIdentifier": {
                    "RoleId": "arn:aws::iam::123456789012:role/MyAppIAMRole"
                },
                "ManagedByStack": false
            }
        ]
    }

For more information, see `Create a CloudFormation template from resources scanned with IaC generator <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/iac-generator-create-template-from-scanned-resources.html>`__ in the *AWS CloudFormation User Guide*.
