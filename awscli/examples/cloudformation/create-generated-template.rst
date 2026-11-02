**To create a generated template from scanned resources**

The following ``create-generated-template`` example creates a generated template named ``MyTemplate`` from scanned resources. ::

    aws cloudformation create-generated-template \
        --generated-template-name MyTemplate \
        --resources file://resources.json

Contents of ``resources.json``::

    [
        {
            "ResourceType": "AWS::EKS::Cluster",
            "LogicalResourceId":"MyCluster",
            "ResourceIdentifier": {
                "ClusterName": "MyAppClusterName"
            }
        },
        {
            "ResourceType": "AWS::AutoScaling::AutoScalingGroup",
            "LogicalResourceId":"MyASG",
            "ResourceIdentifier": {
                "AutoScalingGroupName": "MyAppASGName"
            }
        },
        {
            "ResourceType": "AWS::EKS::Nodegroup",
            "LogicalResourceId":"MyNodegroup",
            "ResourceIdentifier": {
                "NodegroupName": "MyAppNodegroupName"
            }
        },
        {
            "ResourceType": "AWS::IAM::Role",
            "LogicalResourceId":"MyRole",
            "ResourceIdentifier": {
                "RoleId": "arn:aws::iam::123456789012:role/MyAppIAMRole"
            }
        }
    ]

Output::

    {
        "GeneratedTemplateId": "arn:aws:cloudformation:us-west-2:123456789012:generatedtemplate/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Create a CloudFormation template from resources scanned with IaC generator <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/iac-generator-create-template-from-scanned-resources.html>`__ in the *AWS CloudFormation User Guide*.
