**To delete a health check**

The following ``delete-health-check`` example deletes the health check with a ``health-check-id`` of ``a1b2c3d4-5678-90ab-cdef-EXAMPLE11111``. ::

    aws route53 delete-health-check \
        --health-check-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

This command produces no output.

For more information, see `Deleting health checks <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/health-checks-deleting.html>`__ in the *Amazon Route 53 Developer Guide*.
