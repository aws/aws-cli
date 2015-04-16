**To describe the available types of lifecycle hooks**

This example describes the available types of lifecycle hooks::

   aws autoscaling describe-lifecycle-hook-types
   
The following is example output::

  {
    "LifecycleHookTypes": [
        "autoscaling:EC2_INSTANCE_LAUNCHING",
        "autoscaling:EC2_INSTANCE_TERMINATING"
    ]
  }
