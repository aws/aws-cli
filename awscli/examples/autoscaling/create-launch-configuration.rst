**To create a launch configuration**

This example creates a launch configuration. ::

    aws autoscaling create-launch-configuration --launch-configuration-name my-launch-config --image-id ami-c6169af6 --instance-type m1.medium

This command returns to the prompt if successful.

This example creates a launch configuration with a key pair and a bootstrapping script. ::

    aws autoscaling create-launch-configuration --launch-configuration-name my-launch-config --key-name my-key-pair --image-id ami-c6169af6 --instance-type m1.small --user-data file://myuserdata.txt

This example creates a launch configuration based on an existing instance. In addition, it also specifies launch configuration attributes such as a security group, tenancy, Amazon EBS optimization, and a bootstrapping script. ::

    aws autoscaling create-launch-configuration --launch-configuration-name my-launch-config --key-name my-key-pair --instance-id i-7e13c876 --security-groups sg-eb2af88e --instance-type m1.small --user-data file://myuserdata.txt --instance-monitoring Enabled=true --no-ebs-optimized --no-associate-public-ip-address --placement-tenancy dedicated --iam-instance-profile my-autoscaling-role

Add the following parameter to add an Amazon EBS volume with the device name ``/dev/sdh`` and a volume size of 100.

Parameter::

    --block-device-mappings "[{\"DeviceName\": \"/dev/sdh\",\"Ebs\":{\"VolumeSize\":100}}]"

Add the following parameter to add ``ephemeral1`` as an instance store volume with the device name ``/dev/sdc``.

Parameter::

    --block-device-mappings "[{\"DeviceName\": \"/dev/sdc\",\"VirtualName\":\"ephemeral1\"}]"

Add the following parameter to omit a device included on the instance (for example, ``/dev/sdf``).

Parameter::

    --block-device-mappings "[{\"DeviceName\": \"/dev/sdf\",\"NoDevice\":\"\"}]"

For more information about quoting JSON-formatted parameters, see `Using quotation marks with strings in the AWS CLI`_ in the *AWS Command Line Interface User Guide*.

This example creates a launch configuration that uses Spot Instances. ::

    aws autoscaling create-launch-configuration --launch-configuration-name my-launch-config --image-id ami-01e24be29428c15b2 --instance-type c5.large --spot-price "0.50"

For more information, see `Requesting Spot Instances`_ in the *Amazon EC2 Auto Scaling User Guide*.

.. _`Using quotation marks with strings in the AWS CLI`: https://docs.aws.amazon.com/cli/latest/userguide/cli-usage-parameters-quoting-strings.html

.. _`Requesting Spot Instances`: https://docs.aws.amazon.com/autoscaling/ec2/userguide/asg-launch-spot-instances.html
