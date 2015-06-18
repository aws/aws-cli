**To detach a load balancer from an Auto Scaling group**

This example detaches the specified load balancer from the specified Auto Scaling group::

   aws autoscaling detach-load-balancers --load-balancer-names my-lb --auto-scaling-group-name my-asg 
