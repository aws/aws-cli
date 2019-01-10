**To create an Auto Scaling group**

This example creates an Auto Scaling group in a VPC using a launch configuration to specify the type of EC2 instance that Amazon EC2 Auto Scaling creates::

    aws autoscaling create-auto-scaling-group --auto-scaling-group-name my-auto-scaling-group --launch-configuration-name my-launch-config --min-size 1 --max-size 3 --vpc-zone-identifier subnet-41767929c

This example creates an Auto Scaling group in a VPC using a launch template to specify the type of EC2 instance that Amazon EC2 Auto Scaling creates::

    aws autoscaling create-auto-scaling-group --auto-scaling-group-name my-auto-scaling-group --launch-template 'LaunchTemplateName=my_template,Version=2' --min-size 1 --max-size 3 --vpc-zone-identifier subnet-41767929c 

This example creates an Auto Scaling group and configures it to use an Elastic Load Balancing load balancer::

    aws autoscaling create-auto-scaling-group --auto-scaling-group-name my-auto-scaling-group --launch-configuration-name my-launch-config --load-balancer-names my-load-balancer --health-check-type ELB --health-check-grace-period 120

This example creates an Auto Scaling group using a launch configuration. It specifies Availability Zones instead of subnets. It also launches instances into a placement group and sets the termination policy to terminate the oldest instances first::

    aws autoscaling create-auto-scaling-group --auto-scaling-group-name my-auto-scaling-group --launch-configuration-name my-launch-config --min-size 1 --max-size 3 --desired-capacity 1 --placement-group my-placement-group --termination-policies "OldestInstance" --availability-zones us-west-2c

This example creates an Auto Scaling group from the specified EC2 instance and assigns a tag to instances in the group::

    aws autoscaling create-auto-scaling-group --auto-scaling-group-name my-auto-scaling-group --instance-id i-22c99e2a --min-size 1 --max-size 3 --vpc-zone-identifier subnet-41767929 --tags ResourceId=my-auto-scaling-group,ResourceType=auto-scaling-group,Key=Role,Value=WebServer

This example creates an Auto Scaling group using a launch template. It specifies Availability Zones instead of subnets and enables the instance protection setting::

    aws autoscaling create-auto-scaling-group --auto-scaling-group-name my-auto-scaling-group --launch-template 'LaunchTemplateName=my_template,Version=2' --min-size 1 --max-size 3 --desired-capacity 2 --availability-zones us-west-2a us-west-2b us-west-2c --new-instances-protected-from-scale-in
