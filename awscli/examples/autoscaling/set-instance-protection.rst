**To change the instance protection setting for an instance**

This example enables instance protection for the specified instance::

    aws autoscaling set-instance-protection --instance-ids i-93633f9b --auto-scaling-group-name my-auto-scaling-group --protected-from-scale-in

This example disables instance protection for the specified instance::

    aws autoscaling set-instance-protection --instance-ids i-93633f9b --auto-scaling-group-name my-auto-scaling-group --no-protected-from-scale-in
