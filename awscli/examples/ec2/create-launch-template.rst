**Example 1: To create a launch template**

The following ``create-launch-template`` example creates a launch template that specifies the subnet in which to launch the instance , assigns a public IP address and an IPv6 address to the instance, and creates a tag for the instance. ::

    aws ec2 create-launch-template \
        --launch-template-name TemplateForWebServer \
        --version-description WebVersion1 \
        --launch-template-data '{"NetworkInterfaces":[{"AssociatePublicIpAddress":true,"DeviceIndex":0,"Ipv6AddressCount":1,"SubnetId":"subnet-7b16de0c"}],"ImageId":"ami-8c1be5f6","InstanceType":"t2.small","TagSpecifications":[{"ResourceType":"instance","Tags":[{"Key":"purpose","Value":"webserver"}]}]}'

Output::

    {
        "LaunchTemplate": {
            "LatestVersionNumber": 1,
            "LaunchTemplateId": "lt-01238c059e3466abc",
            "LaunchTemplateName": "TemplateForWebServer",
            "DefaultVersionNumber": 1,
            "CreatedBy": "arn:aws:iam::123456789012:user/Bob",
            "CreateTime": "2019-01-27T09:13:24.000Z"
        }
    }

For more information, see `Store instance launch parameters in Amazon EC2 launch templates <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-launch-templates.html>`__ in the *Amazon EC2 User Guide*. For information about quoting JSON-formatted parameters, see `Using quotation marks and literals with strings in the AWS CLI <https://docs.aws.amazon.com/cli/latest/userguide/cli-usage-parameters-quoting-strings.html>`__ in the *AWS Command Line Interface User Guide*.

**Example 2: To create a launch template for Amazon EC2 Auto Scaling**

The following ``create-launch-template`` example creates a launch template with multiple tags and a block device mapping to specify an additional EBS volume when an instance launches. Specify a value for ``Groups`` that corresponds to security groups for the VPC that your Auto Scaling group will launch instances into. Specify the VPC and subnets as properties of the Auto Scaling group. ::

    aws ec2 create-launch-template \
        --launch-template-name TemplateForAutoScaling \
        --version-description AutoScalingVersion1 \
        --launch-template-data '{"NetworkInterfaces":[{"DeviceIndex":0,"AssociatePublicIpAddress":true,"Groups":["sg-7c227019,sg-903004f8"],"DeleteOnTermination":true}],"ImageId":"ami-b42209de","InstanceType":"m4.large","TagSpecifications":[{"ResourceType":"instance","Tags":[{"Key":"environment","Value":"production"},{"Key":"purpose","Value":"webserver"}]},{"ResourceType":"volume","Tags":[{"Key":"environment","Value":"production"},{"Key":"cost-center","Value":"cc123"}]}],"BlockDeviceMappings":[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":100}}]}'

Output::

    {
        "LaunchTemplate": {
            "LatestVersionNumber": 1,
            "LaunchTemplateId": "lt-0123c79c33a54e0abc",
            "LaunchTemplateName": "TemplateForAutoScaling",
            "DefaultVersionNumber": 1,
            "CreatedBy": "arn:aws:iam::123456789012:user/Bob",
            "CreateTime": "2019-04-30T18:16:06.000Z"
        }
    }

For more information, see `Create a launch template for an Auto Scaling group <https://docs.aws.amazon.com/autoscaling/ec2/userguide/create-launch-template.html>`__ in the *Amazon EC2 Auto Scaling User Guide*. For information about quoting JSON-formatted parameters, see `Using quotation marks and literals with strings in the AWS CLI <https://docs.aws.amazon.com/cli/latest/userguide/cli-usage-parameters-quoting-strings.html>`__ in the *AWS Command Line Interface User Guide*.

**Example 3: To create a launch template that specifies encryption of EBS volumes**

The following ``create-launch-template`` example creates a launch template that includes encrypted EBS volumes created from an unencrypted snapshot. It also tags the volumes during creation. If encryption by default is disabled, you must specify the ``"Encrypted"`` option as shown in the following example. If you use the ``"KmsKeyId"`` option to specify a customer managed CMK, you also must specify the ``"Encrypted"`` option even if encryption by default is enabled. ::

    aws ec2 create-launch-template \
        --launch-template-name TemplateForEncryption \
        --launch-template-data file://config.json

Contents of ``config.json``::

    {
        "BlockDeviceMappings":[
            {
                "DeviceName":"/dev/sda1",
                "Ebs":{
                    "VolumeType":"gp2",
                    "DeleteOnTermination":true,
                    "SnapshotId":"snap-0abcdef1234567890",
                    "Encrypted":true,
                    "KmsKeyId":"arn:aws:kms:us-west-2:123456789012:key/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
                }
            }
        ],
        "ImageId":"ami-00068cd7555f543d5",
        "InstanceType":"c5.large",
        "TagSpecifications":[
            {
                "ResourceType":"volume",
                "Tags":[
                    {
                        "Key":"encrypted",
                        "Value":"yes"
                    }
                ]
            }
        ]
    }

Output::

    {
        "LaunchTemplate": {
            "LatestVersionNumber": 1,
            "LaunchTemplateId": "lt-0d5bd51bcf8530abc",
            "LaunchTemplateName": "TemplateForEncryption",
            "DefaultVersionNumber": 1,
            "CreatedBy": "arn:aws:iam::123456789012:user/Bob",
            "CreateTime": "2020-01-07T19:08:36.000Z"
        }
    }

For more information, see `Create an Amazon EBS volume <https://docs.aws.amazon.com/ebs/latest/userguide/ebs-creating-volume.html>`__ and `Enable Amazon EBS encryption by default <https://docs.aws.amazon.com/ebs/latest/userguide/encryption-by-default.html>`__ in the *Amazon EBS User Guide*.
