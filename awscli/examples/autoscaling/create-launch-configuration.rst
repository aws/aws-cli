**Example 1: To create a launch configuration**

The following ``create-launch-configuration`` example creates a simple launch configuration. ::

    aws autoscaling create-launch-configuration \
        --launch-configuration-name my-lc \
        --image-id ami-04d5cc9b88example \
        --instance-type m5.large

This command produces no output.

For more information, see `Creating a launch configuration <https://docs.aws.amazon.com/autoscaling/ec2/userguide/create-launch-config.html>`__ in the *Amazon EC2 Auto Scaling User Guide*.

**Example 2: To create a launch configuration with a security group, key pair, and bootstrapping script**

The following ``create-launch-configuration`` example creates a launch configuration with a security group, a key pair, and a bootstrapping script contained in the user data. ::

    aws autoscaling create-launch-configuration \
        --launch-configuration-name my-lc \
        --image-id ami-04d5cc9b88example \
        --instance-type m5.large \
        --security-groups sg-eb2af88example \
        --key-name my-key-pair \
        --user-data file://myuserdata.txt

Contents of ``myuserdata.txt``::

    #!/bin/bash
    yum update -y
    yum install -y httpd
    systemctl start httpd
    systemctl enable httpd

This command produces no output.

For more information, see `Creating a launch configuration <https://docs.aws.amazon.com/autoscaling/ec2/userguide/create-launch-config.html>`__ in the *Amazon EC2 Auto Scaling User Guide*.

**Example 3: To create a launch configuration with an IAM role**

The following ``create-launch-configuration`` example creates a launch configuration with the instance profile name of an IAM role. ::

    aws autoscaling create-launch-configuration \
        --launch-configuration-name my-lc \
        --image-id ami-04d5cc9b88example \
        --instance-type m5.large \
        --iam-instance-profile my-autoscaling-role 

This command produces no output.

For more information, see `IAM role for applications that run on Amazon EC2 instances <https://docs.aws.amazon.com/autoscaling/ec2/userguide/us-iam-role.html>`__ in the *Amazon EC2 Auto Scaling User Guide*.

**Example 4: To create a launch configuration with detailed monitoring enabled**

The following ``create-launch-configuration`` example creates a launch configuration with EC2 detailed monitoring enabled, which sends EC2 metrics to CloudWatch in 1-minute periods. ::

    aws autoscaling create-launch-configuration \
        --launch-configuration-name my-lc \
        --image-id ami-04d5cc9b88example \
        --instance-type m5.large \
        --instance-monitoring Enabled=true 

This command produces no output.

For more information, see `Configuring monitoring for Auto Scaling instances  <https://docs.aws.amazon.com/autoscaling/ec2/userguide/enable-as-instance-metrics.html>`__ in the *Amazon EC2 Auto Scaling User Guide*.

**Example 5: To create a launch configuration that launches Spot Instances**

The following ``create-launch-configuration`` example creates a launch configuration that uses Spot Instances as the only purchase option. ::

    aws autoscaling create-launch-configuration \
        --launch-configuration-name my-lc \
        --image-id ami-04d5cc9b88example \
        --instance-type m5.large \
        --spot-price "0.50"

This command produces no output.

For more information, see `Requesting Spot Instances <https://docs.aws.amazon.com/autoscaling/ec2/userguide/asg-launch-spot-instances.html>`__ in the *Amazon EC2 Auto Scaling User Guide*.

**Example 6: To create a launch configuration using an EC2 instance**

The following ``create-launch-configuration`` example creates a launch configuration based on the attributes of an existing instance. It overrides the placement tenancy and whether a public IP address is set by including the ``--placement-tenancy`` and ``--no-associate-public-ip-address`` options. ::

    aws autoscaling create-launch-configuration \
        --launch-configuration-name my-lc-from-instance \
        --instance-id i-1234567890abcdef0 \
        --instance-type m5.large \
        --no-associate-public-ip-address \
        --placement-tenancy dedicated 

This command produces no output.

For more information, see `Creating a launch configuration using an EC2 instance <https://docs.aws.amazon.com/autoscaling/ec2/userguide/create-lc-with-instanceID.html>`__ in the *Amazon EC2 Auto Scaling User Guide*.

**Example 7: To create a launch configuration with a block device mapping for an Amazon EBS volume**

The following ``create-launch-configuration`` example creates a launch configuration with a block device mapping for an Amazon EBS ``gp3`` volume with the device name ``/dev/sdh`` and a volume size of 20. ::

    aws autoscaling create-launch-configuration \
        --launch-configuration-name my-lc \
        --image-id ami-04d5cc9b88example \
        --instance-type m5.large \
        --block-device-mappings '[{"DeviceName":"/dev/sdh","Ebs":{"VolumeSize":20,"VolumeType":"gp3"}}]'

This command produces no output.

For more information, see `Block device mappings for volumes on Amazon EC2 instances <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/block-device-mapping-concepts.html>`__ in the *Amazon EC2 User Guide*.

For information about the syntax for quoting JSON-formatted parameter values, see `Using quotation marks with strings in the AWS CLI <https://docs.aws.amazon.com/cli/latest/userguide/cli-usage-parameters-quoting-strings.html>`__ in the *AWS Command Line Interface User Guide*. 

**Example 8: To create a launch configuration with a block device mapping for an instance store volume**

The following ``create-launch-configuration`` example creates a launch configuration with ``ephemeral1`` as an instance store volume with the device name ``/dev/sdc``. ::

    aws autoscaling create-launch-configuration \
        --launch-configuration-name my-lc \
        --image-id ami-04d5cc9b88example \
        --instance-type m5.large \
        --block-device-mappings '[{"DeviceName":"/dev/sdc","VirtualName":"ephemeral1"}]'

This command produces no output.

For more information, see `Instance store temporary block storage for EC2 instances <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/InstanceStorage.html>`__ in the *Amazon EC2 User Guide*.

For information about the syntax for quoting JSON-formatted parameter values, see `Using quotation marks with strings in the AWS CLI <https://docs.aws.amazon.com/cli/latest/userguide/cli-usage-parameters-quoting-strings.html>`__ in the *AWS Command Line Interface User Guide*. 

**Example 9: To create a launch configuration and suppress a block device from attaching at launch time**

The following ``create-launch-configuration`` example creates a launch configuration that suppresses a block device specified by the block device mapping of the AMI (for example, ``/dev/sdf``). ::

    aws autoscaling create-launch-configuration \
        --launch-configuration-name my-lc \
        --image-id ami-04d5cc9b88example \
        --instance-type m5.large \
        --block-device-mappings '[{"DeviceName":"/dev/sdf","NoDevice":""}]'

This command produces no output.

For more information, see `Block device mappings for volumes on Amazon EC2 instances <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/block-device-mapping-concepts.html>`__ in the *Amazon EC2 User Guide*.

For information about the syntax for quoting JSON-formatted parameter values, see `Using quotation marks with strings in the AWS CLI <https://docs.aws.amazon.com/cli/latest/userguide/cli-usage-parameters-quoting-strings.html>`__ in the *AWS Command Line Interface User Guide*. 
