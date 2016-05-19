**To change the instance protection setting for an instance**

This example enables instance protection for the specified instance::

    aws autoscaling set-instance-protection --instance-ids i-93633f9b --protected-from-scale-in

This example disables instance protection for the specified instance::

    aws autoscaling set-instance-protection --instance-ids i-93633f9b --no-protected-from-scale-in
