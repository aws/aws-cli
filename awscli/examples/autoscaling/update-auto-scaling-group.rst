**To update the size of an Auto Scaling group**

This example updates the desired capacity, maximum size, and minimum size of the specified Auto Scaling group. ::

    aws autoscaling update-auto-scaling-group --auto-scaling-group-name my-asg --desired-capacity 6 --max-size 10 --min-size 2 

This command returns to the prompt if successful.

**To add Elastic Load Balancing health checks and specify which Availability Zones and subnets to use**

This example updates the specified Auto Scaling group to add Elastic Load Balancing health checks. This command also updates the value of ``--vpc-zone-identifier``. This helps you change the Availability Zones where the instances are located as well as the subnets. ::

    aws autoscaling update-auto-scaling-group --auto-scaling-group-name my-asg --health-check-type ELB --health-check-grace-period 600 --vpc-zone-identifier "subnet-5ea0c127,subnet-6194ea3b,subnet-c934b782"

**To update the placement group and termination policy**

This example updates the placement group and termination policy to use:

    aws autoscaling update-auto-scaling-group --auto-scaling-group-name my-asg --placement-group my-placement-group --termination-policies "OldestInstance" 

**To use the latest version of the launch template**

This example updates the specified Auto Scaling group to use the latest version of the specified launch template. ::

    aws autoscaling update-auto-scaling-group --auto-scaling-group-name my-asg --launch-template LaunchTemplateId=lt-1234567890abcde12,Version='$Latest'

**To use a specific version of the launch template**

This example updates the specified Auto Scaling group to use a specific version of the specified launch template. ::

    aws autoscaling update-auto-scaling-group --auto-scaling-group-name my-asg --launch-template LaunchTemplateName=my-template-for-auto-scaling,Version='2'

**To define a mixed instances policy and enable capacity rebalancing**

This example updates the specified Auto Scaling group to use a mixed instances policy and enables capacity rebalancing. This structure lets you specify groups with Spot and On-Demand capacities and use different launch templates for different architectures. ::

    aws autoscaling update-auto-scaling-group --cli-input-json file://~/config.json 

Contents of ``config.json`` file::

  {
      "AutoScalingGroupName": "my-asg",
      "CapacityRebalance": true,
      "MixedInstancesPolicy": {
          "LaunchTemplate": {
              "LaunchTemplateSpecification": {
                  "LaunchTemplateName": "my-launch-template-for-x86",
                  "Version": "$Latest"
              },
              "Overrides": [
                  {
                      "InstanceType": "c6g.large",
                      "LaunchTemplateSpecification": {
                          "LaunchTemplateName": "my-launch-template-for-arm",
                          "Version": "$Latest"
                      }
                  },
                  {
                      "InstanceType": "c5.large"
                  },
                  {
                    "InstanceType": "c5a.large"
                  }
              ]
          },
          "InstancesDistribution": {
              "OnDemandPercentageAboveBaseCapacity": 50,
              "SpotAllocationStrategy": "capacity-optimized"
          }
      }
  }

For more information, see `Auto Scaling groups`_ in the *Amazon EC2 Auto Scaling User Guide*.

.. _`Auto Scaling groups`: https://docs.aws.amazon.com/autoscaling/ec2/userguide/AutoScalingGroup.html
