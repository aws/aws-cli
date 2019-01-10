**To create an Auto Scaling group using a launch configuration**

This example creates an Auto Scaling group in a VPC using a launch configuration to specify the type of EC2 instance that Amazon EC2 Auto Scaling creates::

    aws autoscaling create-auto-scaling-group --auto-scaling-group-name my-asg --launch-configuration-name my-launch-config --min-size 1 --max-size 3 --vpc-zone-identifier "subnet-5ea0c127,subnet-6194ea3b,subnet-c934b782"

This example creates an Auto Scaling group and configures it to use an Elastic Load Balancing load balancer::

    aws autoscaling create-auto-scaling-group --auto-scaling-group-name my-asg --launch-configuration-name my-launch-config --load-balancer-names my-load-balancer --health-check-type ELB --health-check-grace-period 120 --min-size 1 --max-size 3 --vpc-zone-identifier "subnet-5ea0c127,subnet-6194ea3b,subnet-c934b782"

This example specifies a desired capacity as well as a minimum and maximum capacity. It also launches instances into a placement group and sets the termination policy to terminate the oldest instances first::

    aws autoscaling create-auto-scaling-group --auto-scaling-group-name my-asg --launch-configuration-name my-launch-config --min-size 1 --max-size 3 --desired-capacity 1 --placement-group my-placement-group --termination-policies "OldestInstance" --availability-zones us-west-2c

**To create an Auto Scaling group using an EC2 instance**

This example creates an Auto Scaling group from the specified EC2 instance and assigns a tag to instances in the group::

    aws autoscaling create-auto-scaling-group --auto-scaling-group-name my-asg --instance-id i-22c99e2a --min-size 1 --max-size 3 --vpc-zone-identifier "subnet-5ea0c127,subnet-6194ea3b,subnet-c934b782" --tags "ResourceId=my-asg,ResourceType=auto-scaling-group,Key=Role,Value=WebServer,PropagateAtLaunch=true"

**To create an Auto Scaling group using a launch template**

This example creates an Auto Scaling group in a VPC using a launch template to specify the type of EC2 instance that Amazon EC2 Auto Scaling creates::

    aws autoscaling create-auto-scaling-group --auto-scaling-group-name my-asg --launch-template "LaunchTemplateName=my-template-for-auto-scaling,Version=1" --min-size 1 --max-size 3 --vpc-zone-identifier "subnet-5ea0c127,subnet-6194ea3b,subnet-c934b782"
    
This example uses the default version of the specified launch template. It specifies Availability Zones and subnets and enables the instance protection setting::

    aws autoscaling create-auto-scaling-group --auto-scaling-group-name my-asg --launch-template LaunchTemplateId=lt-0a4872e2c396d941c --min-size 1 --max-size 3 --desired-capacity 2 --availability-zones us-west-2a us-west-2b us-west-2c --vpc-zone-identifier "subnet-5ea0c127,subnet-6194ea3b,subnet-c934b782" --new-instances-protected-from-scale-in
    
This example creates an Auto Scaling group that launches a single instance using a launch template to optionally specify the ID of an existing network interface (ENI ID) to use. It specifies an Availability Zone that matches the specified network interface::

    aws autoscaling create-auto-scaling-group --auto-scaling-group-name my-asg-single-instance --launch-template "LaunchTemplateName=my-single-instance-asg-template,Version=2" --min-size 1 --max-size 1 --availability-zones us-west-2a

This example creates an Auto Scaling group with a lifecycle hook that supports a custom action at instance termination::

   aws autoscaling create-auto-scaling-group --cli-input-json file://~/config.json

Contents of config.json file::

  {
      "AutoScalingGroupName": "my-asg",
      "LaunchTemplate": {
          "LaunchTemplateId": "lt-0a4872e2c396d941c"
      },
      "LifecycleHookSpecificationList": [{
          "LifecycleHookName": "my-hook",
          "LifecycleTransition": "autoscaling:EC2_INSTANCE_TERMINATING",
          "NotificationTargetARN": "arn:aws:sqs:us-west-2:123456789012:my-sqs-queue",
          "RoleARN": "arn:aws:iam::123456789012:role/my-notification-role",
          "HeartbeatTimeout": 300,
          "DefaultResult": "CONTINUE"
      }],
      "MinSize": 1,
      "MaxSize": 5,
      "VPCZoneIdentifier": "subnet-5ea0c127,subnet-6194ea3b,subnet-c934b782",
      "Tags": [{
            "ResourceType": "auto-scaling-group",
            "ResourceId": "my-asg",
            "PropagateAtLaunch": true,
            "Value": "test",
            "Key": "environment"
      }]
  }

For more information, see the `Amazon EC2 Auto Scaling User Guide`_.

.. _`Amazon EC2 Auto Scaling User Guide`: https://docs.aws.amazon.com/autoscaling/ec2/userguide/what-is-amazon-ec2-auto-scaling.html
