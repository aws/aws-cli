**To pause running until a load balancer exists**

The following ``wait load-balancer-exists`` example pauses and resumes running only after it confirms that the specified load balancer exists. ::

    aws elbv2 wait load-balancer-exists \
        --load-balancer-arns arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/my-load-balancer/50dc6c495c0c9188

This command produces no output.

For more information, see `Application Load Balancers <https://docs.aws.amazon.com/elasticloadbalancing/latest/application/application-load-balancers.html>`__ in the *Application Load Balancers User Guide*.
