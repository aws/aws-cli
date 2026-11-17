**To create an AWS CloudFormation stack**

The following ``create-stack`` example creates a stack with the name ``myteststack`` using the ``sampletemplate.json`` template. ::

    aws cloudformation create-stack \
        --stack-name myteststack \
        --template-body file://sampletemplate.json \
        --parameters ParameterKey=KeyPairName,ParameterValue=TestKey ParameterKey=SubnetIDs,ParameterValue=SubnetID1\\,SubnetID2

Contents of ``sampletemplate.json``::

    {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "Sample template that creates an Amazon EC2 instance in the first of the specified subnets.",
        "Parameters": {
            "KeyPairName": {
                "Type": "AWS::EC2::KeyPair::KeyName",
                "Description": "Name of an existing EC2 key pair for SSH access to the instance."
            },
            "SubnetIDs": {
                "Type": "CommaDelimitedList",
                "Description": "Comma-delimited list of subnet IDs."
            }
        },
        "Resources": {
            "MyInstance": {
                "Type": "AWS::EC2::Instance",
                "Properties": {
                    "ImageId": "ami-0abcdef1234567890",
                    "InstanceType": "t3.micro",
                    "KeyName": {
                        "Ref": "KeyPairName"
                    },
                    "SubnetId": {
                        "Fn::Select": [
                            "0",
                            {
                                "Ref": "SubnetIDs"
                            }
                        ]
                    }
                }
            }
        }
    }

Output::

    {
        "StackId": "arn:aws:cloudformation:us-west-2:123456789012:stack/myteststack/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Managing AWS resources as a single unit with CloudFormation stacks <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacks.html>`__ in the *AWS CloudFormation User Guide*.
