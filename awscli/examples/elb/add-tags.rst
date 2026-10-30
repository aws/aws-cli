**To add a tag to a load balancer**

The following ``add-tags`` example adds tags to the specified load balancer. ::

    aws elb add-tags \
        --load-balancer-name my-load-balancer \
        --tags "Key=project,Value=lima" "Key=department,Value=digital-media"

This command produces no output.

For more information, see `Tag your Classic Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/add-remove-tags.html>`__ in the *Classic Load Balancers Guide*.
