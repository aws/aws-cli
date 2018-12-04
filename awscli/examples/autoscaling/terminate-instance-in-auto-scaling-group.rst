**To terminate an instance in an Auto Scaling group**

This example terminates the specified instance from the specified Auto Scaling group without updating the size of the group::

    aws autoscaling terminate-instance-in-auto-scaling-group --instance-id i-93633f9b --no-should-decrement-desired-capacity

Auto Scaling launches a replacement instance after the specified instance terminates.
