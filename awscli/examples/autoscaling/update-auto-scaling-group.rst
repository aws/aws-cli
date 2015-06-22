**To update an Auto Scaling group**

This example updates the specified Auto Scaling group to use Elastic Load Balancing health checks::

    aws autoscaling update-auto-scaling-group --auto-scaling-group-name my-test-asg --health-check-type ELB --health-check-grace-period 60

This example updates the launch configuration, minimum and maximum size of the group, and which subnet to use::

    aws autoscaling update-auto-scaling-group --auto-scaling-group-name basic-auto-scaling-group --launch-configuration-name new-launch-config --min-size 1 --max-size 3 --vpc-zone-identifier subnet-41767929

This example updates the desired capacity, default cooldown, placement group, termination policy, and which Availability Zone to use::

    aws autoscaling update-auto-scaling-group --auto-scaling-group-name extended-auto-scaling-group-2 --default-cooldown 600 --placement-group sample-placement-group --termination-policies "OldestInstance" --availability-zones us-west-2c
