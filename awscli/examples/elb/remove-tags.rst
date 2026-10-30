**To remove tags from a load balancer**

The following ``remove-tags`` example removes a tag from the specified load balancer. ::

    aws elb remove-tags \
        --load-balancer-name my-load-balancer \
        --tags project

This command produces no output.
