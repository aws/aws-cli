**To create a launch configuration**

This example creates a launch configuration::

     aws autoscaling create-launch-configuration --launch-configuration-name my-test-lc --image-id ami-c6169af6 --instance-type m1.medium

This example creates a launch configuration that uses Spot Instances::

    aws autoscaling create-launch-configuration --launch-configuration-name my-test-lc --image-id ami-c6169af6 --instance-type m1.medium --spot-price "0.50"

This example creates a launch configuration with a key pair and bootstrapping script::

    aws autoscaling create-launch-configuration --launch-configuration-name detailed-launch-config --key-name qwikLABS-L238-20080 --image-id ami-c6169af6 --instance-type m1.small --user-data file://labuserdata.txt

This example creates a launch configuration based on an existing instance. In addition, it also specifies launch configuration attributes such as a security group, tenancy, Amazon EBS optimization, and bootstrapping script::

    aws autoscaling create-launch-configuration --launch-configuration-name detailed-launch-config --key-name qwikLABS-L238-20080 --instance-id i-7e13c876 --security-groups sg-eb2af88e --instance-type m1.small --user-data file://labuserdata.txt --instance-monitoring Enabled=true --no-ebs-optimized --no-associate-public-ip-address --placement-tenancy dedicated --iam-instance-profile "autoscalingrole"

Add the following parameter to your ``create-launch-configuration`` command to add an Amazon EBS volume with the device name ``/dev/sdh`` and a volume size of 100.

Parameter::

  --block-device-mappings "[{\"DeviceName\": \"/dev/sdh\",\"Ebs\":{\"VolumeSize\":100}}]"

Add the following parameter to your ``create-launch-configuration`` command to add ``ephemeral1`` as an instance store volume with the device name ``/dev/sdc``.

Parameter::

  --block-device-mappings "[{\"DeviceName\": \"/dev/sdc\",\"VirtualName\":\"ephemeral1\"}]"

Add the following parameter to your ``create-launch-configuration`` command to omit a device included on the instance (for example, ``/dev/sdf``).

Parameter::

  --block-device-mappings "[{\"DeviceName\": \"/dev/sdf\",\"NoDevice\":\"\"}]"
