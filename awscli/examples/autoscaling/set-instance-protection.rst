**To change the instance protection setting for an instance**

This example enables instance protection for the specified instance. ::

    aws autoscaling set-instance-protection --instance-ids i-061c63c5eb45f0416 --auto-scaling-group-name my-asg --protected-from-scale-in

This example disables instance protection for the specified instance. ::

    aws autoscaling set-instance-protection --instance-ids i-061c63c5eb45f0416 --auto-scaling-group-name my-asg --no-protected-from-scale-in

This command returns to the prompt if successful.
