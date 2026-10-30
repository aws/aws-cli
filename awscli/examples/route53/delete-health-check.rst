**To delete a health check**

The following ``delete-health-check`` example deletes the health check with a ``health-check-id`` of ``e75b48d9-547a-4c3d-88a5-ae4002397608``. ::

    aws route53 delete-health-check \
        --health-check-id e75b48d9-547a-4c3d-88a5-ae4002397608

This command produces no output.

For more information, see `Deleting health checks <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/health-checks-deleting.html>`__ in the *Amazon Route 53 Developer Guide*.
