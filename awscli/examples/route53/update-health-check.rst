**To update a health check**

The following ``update-health-check`` command updates a health check with a ``health-check-id`` of ``d472caf9-a8ff-4d92-87b7-c9378EXAMPLE`` and the JSON-formatted configuration in the file ``C:\temp\update-health-check.json``::

  aws route53 update-health-check --health-check-id d472caf9-a8ff-4d92-87b7-c9378EXAMPLE --cli-input-json file://C:\temp\update-health-check.json

To add the health check to a Route 53 resource record set, use the ``change-resource-record-sets`` command.

For more information, see `Creating Amazon Route 53 Health Checks and Configuring DNS Failover`_ in the *Amazon Route 53 Developer Guide*.

.. _`Creating Amazon Route 53 Health Checks and Configuring DNS Failover`: http://docs.aws.amazon.com/Route53/latest/DeveloperGuide/dns-failover.html

  
**Health check that monitors an endpoint**

Use the following syntax to update a health check that monitors an endpoint::

  {
	"EnableSNI": true|false,
    "FailureThreshold": integer between 1 and 10,
    "FullyQualifiedDomainName": "domain name of the endpoint to check--all Types except TCP",
    "HealthCheckVersion": current health check version,
    "Inverted": true|false,
    "IPAddress": "IP address of the endpoint to check",
    "Port": port on the endpoint to check--required when Type is "TCP",
	"Regions": [
	  "supported region", 
	  ...
	],
    "ResourcePath": "path of the file that you want Amazon Route 53 to request--all Types except TCP",
    "SearchString": "if Type is HTTP_STR_MATCH or HTTPS_STR_MATCH, the string to search for in the response body from the specified resource"
  }

**Health check that monitors a CloudWatch metric**

Use the following syntax to update a health check that monitors a CloudWatch metric::

  {
    "AlarmIdentifier":{
      "Name": "name of CloudWatch alarm",
      "Region": "region that CloudWatch alarm was created in"
    },
    "HealthCheckVersion": current health check version,
    "InsufficientDataHealthStatus": "Healthy | Unhealthy | LastKnownStatus",
    "Inverted": true | false
  }

**Health check that monitors other Route 53 health checks**

Use the following syntax to update a health check that monitors other Route 53 health checks::

  {
    "ChildHealthChecks":[
      "health check ID",
      ...
    ],
    "HealthCheckVersion": current health check version,
    "HealthThreshold": number of the health checks that are associated with a CALCULATED health check that must be healthy,
    "Inverted": true | false
  }