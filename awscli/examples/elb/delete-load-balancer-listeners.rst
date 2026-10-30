**To delete a listener from your load balancer**

The following ``delete-load-balancer-listeners`` example deletes the listener for the specified port from the specified load balancer. ::

    aws elb delete-load-balancer-listeners --load-balancer-name my-load-balancer --load-balancer-ports 80
