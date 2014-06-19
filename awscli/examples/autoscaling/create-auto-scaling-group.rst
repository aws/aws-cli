**To launch an Auto Scaling group**

The following ``create-auto-scaling-group`` command launches an Auto Scaling group in a VPC::

     aws autoscaling create-auto-scaling-group --auto-scaling-group-name basic-auto-scaling-group --launch-configuration-name basic-launch-config --min-size 1 --max-size 3 --vpc-zone-identifier subnet-41767929c

The following ``create-auto-scaling-group`` command launches an Auto Scaling group and configures it to use Elastic Load Balancing::

    aws autoscaling create-auto-scaling-group --auto-scaling-group-name extended-auto-scaling-group-2 --launch-configuration-name basic-launch-config-3 --load-balancer-names "sample-lb" --health-check-type ELB --health-check-grace-period 120

The following ``create-auto-scaling-group`` command launches an Auto Scaling group. It specifies Availability Zones (using the ``availability-zones`` parameter) instead of subnets. It also launches any instances into a placement group and sets the termination policy to terminate the oldest instances first::

    aws autoscaling create-auto-scaling-group --auto-scaling-group-name extended-auto-scaling-group-2 --launch-configuration-name basic-launch-config-3 --min-size 1 --max-size 3 --desired-capacity 2 --default-cooldown 600 --placement-group sample-placement-group --termination-policies "OldestInstance" --availability-zones us-west-2c

The following ``create-auto-scaling-group`` command launches an Auto Scaling group and assigns a tag to instances in the group::

    aws autoscaling create-auto-scaling-group --auto-scaling-group-name tags-auto-scaling-group --instance-id i-22c99e2a --min-size 1 --max-size 3 --vpc-zone-identifier subnet-41767929 --tags ResourceId=tags-auto-scaling-group,ResourceType=auto-scaling-group,Key=Role,Value=WebServer

For more information, see `Basic Auto Scaling Configuration`_ in the *Auto Scaling Developer Guide*.

.. _`Basic Auto Scaling Configuration`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/US_BasicSetup.html

