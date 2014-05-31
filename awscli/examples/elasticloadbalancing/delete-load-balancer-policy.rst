**To delete a policy from your load balancer**

This example deletes a policy.  The policy must not be enabled on any listener.

Command::

      aws elb delete-load-balancer-policy --load-balancer-name MyHTTPSLoadBalancer --policy-name EnableDurationStickinessPolicy


Output::

      {}

