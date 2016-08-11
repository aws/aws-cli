**To remove tags from a load balancer**

This example removes the specified tags from the specified load balancer.

Command::

  aws elbv2 remove-tags --resource-arns arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/my-load-balancer/50dc6c495c0c9188 --tag-keys project department
