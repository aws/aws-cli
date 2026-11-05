**To get information about a health check**

The following ``get-health-check`` example gets information about the health check that has a ``health-check-id`` of ``a1b2c3d4-5678-90ab-cdef-EXAMPLE11111``. ::

    aws route53 get-health-check \
        --health-check-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "HealthCheck": {
            "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "CallerReference": "2014-04-01-18:47",
            "HealthCheckConfig": {
                "IPAddress": "192.0.2.44",
                "Port": 80,
                "Type": "HTTP",
                "ResourcePath": "/docs/route53-health-check.html",
                "FullyQualifiedDomainName": "example.com",
                "RequestInterval": 30,
                "FailureThreshold": 3,
                "MeasureLatency": false,
                "Inverted": false,
                "Disabled": false,
                "EnableSNI": false
            },
            "HealthCheckVersion": 1
        }
    }

For more information, see `Creating, updating, and deleting health checks <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/health-checks-creating-deleting.html>`__ in the *Amazon Route 53 Developer Guide*.
