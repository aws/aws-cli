**To list the health checks associated with the current AWS account**

The following ``list-health-checks`` example lists detailed information about the first 100 health checks that are associated with the current AWS account. ::

    aws route53 list-health-checks

Output::

    {
        "HealthChecks": [
            {
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
        ]
    }

If you have more than 100 health checks, or if you want to list them in groups smaller than 100, include the ``--maxitems`` parameter. For example, to list health checks one at a time, use the following command. ::

    aws route53 list-health-checks \
        --max-items 1

To view the next health check, take the value of ``NextToken`` from the response to the previous command, and include it in the ``--starting-token`` parameter, as shown in the following example. ::

    aws route53 list-health-checks \
        --max-items 1 \
        --starting-token Z3M3LMPEXAMPLE

For more information, see `Creating, updating, and deleting health checks <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/health-checks-creating-deleting.html>`__ in the *Amazon Route 53 Developer Guide*.
