**To add a tag to a load balancer**

The following ``add-tags`` example adds tags to the specified load balancer. ::

    aws elb add-tags \
        --load-balancer-name my-load-balancer \
        --tags "Key=project,Value=lima" "Key=department,Value=digital-media"

