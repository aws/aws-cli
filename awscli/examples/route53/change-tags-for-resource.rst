**Example 1: To add a tag to a health check**

The following ``change-tags-for-resource`` example adds a tag named ``owner`` to a health check resource specified by ID. ::

    aws route53 change-tags-for-resource \
        --resource-type healthcheck \
        --resource-id 6233434j-18c1-34433-ba8e-3443434 \
        --add-tags Key=owner,Value=myboss

This command produces no output.

**Example 2: To remove a tag from a hosted zone**

The following ``change-tags-for-resource`` example removes a tag named ``owner`` from a hosted zone resource specified by ID. ::

    aws route53 change-tags-for-resource \
        --resource-type hostedzone \
        --resource-id Z1523434445 \
        --remove-tag-keys owner

This command produces no output.

For more information, see `Tagging Amazon Route 53 resources <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/tagging-resources.html>`__ in the *Amazon Route 53 Developer Guide*.
