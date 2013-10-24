**To launch an Auto Scaling group**

The following ``create-auto-scaling-group`` command launches an Auto Scaling group::

     aws autoscaling create-auto-scaling-group --auto-scaling-group-name my-test-windows-asg --launch-configuration-name my-test-windows-lc --min-size 0 --max-size 1 --desired-capacity 1 --availability-zones us-west-2c

For more information, see `Basic Auto Scaling Configuration`_ in the *Auto Scaling Developer Guide*.

.. _`Basic Auto Scaling Configuration`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/US_BasicSetup.html
