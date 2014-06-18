**To set the health check type to Elastic Load Balancing**

The following ``update-auto-scaling-group`` command changes the health check type for the specified Auto Scaling group::

    aws autoscaling update-auto-scaling-group --auto-scaling-group-name my-test-asg --health-check-type ELB --health-check-grace-period 60


For more information, see `Add an Elastic Load Balancing Health Check to your Auto Scaling Group`_ in the *Auto Scaling Developer Guide*.

.. _`Add an Elastic Load Balancing Health Check to your Auto Scaling Group`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/as-add-elb-healthcheck.html

