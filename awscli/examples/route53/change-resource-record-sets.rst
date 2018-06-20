**To create, update, or delete a resource record set**

The following ``change-resource-record-sets`` command creates a resource record set using the ``hosted-zone-id`` ``Z1R8UBAEXAMPLE`` and the JSON-formatted configuration in the file ``C:\temp\change-resource-record-sets.json``::

  aws route53 change-resource-record-sets --hosted-zone-id Z1R8UBAEXAMPLE --change-batch file://C:\temp\change-resource-record-sets.json

For more information, see `ChangeResourceRecordSets`_ in the *Amazon Route 53 API Reference*.

.. _`ChangeResourceRecordSets`: http://docs.aws.amazon.com/Route53/latest/APIReference/API_ChangeResourceRecordSets.html


The configuration in the JSON file depends on the kind of resource record set you want to create:

- Basic

- Alias

- Failover

- Failover Alias

- Geolocation

- Geolocation Alias

- Latency

- Latency Alias

- Multivalue Answer

- Weighted

- Weighted Alias


**Basic Syntax**::

  {
    "ChangeBatch":
    {
      "Comment": "optional comment about the changes in this change batch request",
      "Changes": [
        {
          "Action": "CREATE"|"DELETE"|"UPSERT",
          "ResourceRecordSet": {
            "Name": "DNS domain name",
            "Type": "SOA"|"A"|"TXT"|"NS"|"CNAME"|"MX"|"PTR"|"SRV"|"SPF"|"AAAA",
            "TTL": time to live in seconds,
            "ResourceRecords": [
              {
                "Value": "applicable value for the record type"
              },
              {...}
            ]
          }
        },
        {...}
      ]
    }
  }


**Alias Syntax**::

  {
    "ChangeBatch":
    {
      "Comment": "optional comment about the changes in this change batch request",
      "Changes": [
        {
          "Action": "CREATE"|"DELETE"|"UPSERT",
          "ResourceRecordSet": {
            "Name": "DNS domain name",
            "Type": "SOA"|"A"|"TXT"|"NS"|"CNAME"|"MX"|"PTR"|"SRV"|"SPF"|"AAAA",
            "AliasTarget": {
              "DNSName": "DNS domain name for your AWS resource or for another resource record set in this hosted zone",
              "EvaluateTargetHealth": true|false,
              "HostedZoneId": "hosted zone ID for your AWS resource"
            },
            "HealthCheckId": "optional ID of an Amazon Route 53 health check"
          }
        },
        {...}
      ]
    }
  }

  
**Failover Syntax**::

  {
    "ChangeBatch":
    {
      "Comment": "optional comment about the changes in this change batch request",
      "Changes": [
        {
          "Action": "CREATE"|"DELETE"|"UPSERT",
          "ResourceRecordSet": {
            "Name": "DNS domain name",
            "Type": "SOA"|"A"|"TXT"|"NS"|"CNAME"|"MX"|"PTR"|"SRV"|"SPF"|"AAAA",
            "SetIdentifier": "unique description for this resource record set",
            "Failover": "PRIMARY" | "SECONDARY",
            "TTL": time to live in seconds,
            "ResourceRecords": [
              {
                "Value": "applicable value for the record type"
              },
              {...}
            ],
            "HealthCheckId": "ID of an Amazon Route 53 health check"
          }
        },
        {...}
      ]
    }
  }

**Failover Alias Syntax**::

  {
    "ChangeBatch":
    {
      "Comment": "optional comment about the changes in this change batch request",
      "Changes": [
        {
          "Action": "CREATE"|"DELETE"|"UPSERT",
          "ResourceRecordSet": {
            "Name": "DNS domain name",
            "Type": "SOA"|"A"|"TXT"|"NS"|"CNAME"|"MX"|"PTR"|"SRV"|"SPF"|"AAAA",
            "SetIdentifier": "unique description for this resource record set",
            "Failover": "PRIMARY" | "SECONDARY",
            "AliasTarget": {
              "DNSName": "DNS domain name for your AWS resource or for another resource record set in this hosted zone",
              "EvaluateTargetHealth": true|false,
              "HostedZoneId": "hosted zone ID for your AWS resource"
            },
            "HealthCheckId": "optional ID of an Amazon Route 53 health check"
          }
        },
        {...}
      ]
    }
  }


**Geolocation Syntax**::

  {
    "ChangeBatch":
    {
      "Changes": [
        {
          "Action": "CREATE"|"DELETE"|"UPSERT",
          "ResourceRecordSet": {
		    "GeoLocation": {
		      "ContinentCode": "two-letter continent code",
              "CountryCode": "two-letter country code",
              "SubdivisionCode": "subdivision code"
            },
            "HealthCheckId": "optional ID of an Amazon Route 53 health check"
            "Name": "DNS domain name",
            "ResourceRecords": [
              {
                "Value": "applicable value for the record type"
              },
              {...}
            ],
            "SetIdentifier": "unique description for this resource record set",
            "TTL": time to live in seconds,
            "Type": "SOA"|"A"|"TXT"|"NS"|"CNAME"|"MX"|"PTR"|"SRV"|"SPF"|"AAAA"
          }
        },
        {...}
      ],
      "Comment": "optional comment about the changes in this change batch request"
    }
  }

**Geolocation Alias Syntax**::

  {
    "ChangeBatch":
    {
      "Changes": [
        {
          "Action": "CREATE"|"DELETE"|"UPSERT",
          "ResourceRecordSet": {
            "AliasTarget": {
              "DNSName": "DNS domain name for your AWS resource or for another resource record set in this hosted zone",
              "EvaluateTargetHealth": true|false,
              "HostedZoneId": "hosted zone ID for your AWS resource"
            },
		    "GeoLocation": {
              "ContinentCode": "two-letter continent code",
              "CountryCode": "two-letter country code",
              "SubdivisionCode": "subdivision code"
            },
            "HealthCheckId": "optional ID of an Amazon Route 53 health check",
            "Name": "DNS domain name",
            "SetIdentifier": "unique description for this resource record set",
            "Type": "SOA"|"A"|"TXT"|"NS"|"CNAME"|"MX"|"PTR"|"SRV"|"SPF"|"AAAA"
          }
        },
        {...}
      ],
      "Comment": "optional comment about the changes in this change batch request"
    }
  }

  
**Latency Syntax**::

  {
    "ChangeBatch":
    {
      "Comment": "optional comment about the changes in this change batch request",
      "Changes": [
        {
          "Action": "CREATE"|"DELETE"|"UPSERT",
          "ResourceRecordSet": {
            "Name": "DNS domain name",
            "Type": "SOA"|"A"|"TXT"|"NS"|"CNAME"|"MX"|"PTR"|"SRV"|"SPF"|"AAAA",
            "SetIdentifier": "unique description for this resource record set",
            "Region": "Amazon EC2 region name",
            "TTL": time to live in seconds,
            "ResourceRecords": [
              {
                "Value": "applicable value for the record type"
              },
              {...}
            ],
            "HealthCheckId": "optional ID of an Amazon Route 53 health check"
          }
        },
        {...}
      ]
    }
  }
  

**Latency Alias Syntax**::

  {
    "ChangeBatch":
    {
      "Comment": "optional comment about the changes in this change batch request",
      "Changes": [
        {
          "Action": "CREATE"|"DELETE"|"UPSERT",
          "ResourceRecordSet": {
            "Name": "DNS domain name",
            "Type": "SOA"|"A"|"TXT"|"NS"|"CNAME"|"MX"|"PTR"|"SRV"|"SPF"|"AAAA",
            "SetIdentifier": "unique description for this resource record set",
            "Region": "Amazon EC2 region name",
            "AliasTarget": {
              "HostedZoneId": "hosted zone ID for your AWS resource",
              "DNSName": "DNS domain name for your AWS resource or for another resource record set in this hosted zone",
              "EvaluateTargetHealth": true|false
            },
            "HealthCheckId": "optional ID of an Amazon Route 53 health check"
          }
        },
        {...}
      ]
    }
  }
  
  
**Multivalue Answer Syntax**::

  {
    "ChangeBatch":
    {
      "Comment": "optional comment about the changes in this change batch request",
      "Changes": [
        {
          "Action": "CREATE"|"DELETE"|"UPSERT",
          "ResourceRecordSet": {
            "HealthCheckId": "optional ID of an Amazon Route 53 health check",
            "MultiValueAnswer": true|false,
            "Name": "DNS domain name",
            "ResourceRecords": [
              {
                "Value": "applicable value for the record type"
              },
              {...}
            ],
            "SetIdentifier": "unique description for this resource record set",
            "TTL": time to live in seconds,
            "Type": "SOA"|"A"|"TXT"|"NS"|"CNAME"|"MX"|"PTR"|"SRV"|"SPF"|"AAAA"
          }
        },
        {...}
      ]
    }
  }


**Weighted Syntax**::

  {
    "ChangeBatch":
    {
      "Comment": "optional comment about the changes in this change batch request",
      "Changes": [
        {
          "Action": "CREATE"|"DELETE"|"UPSERT",
          "ResourceRecordSet": {
            "Name": "DNS domain name",
            "Type": "SOA"|"A"|"TXT"|"NS"|"CNAME"|"MX"|"PTR"|"SRV"|"SPF"|"AAAA",
            "SetIdentifier": "unique description for this resource record set",
            "Weight": value between 0 and 255,
            "TTL": time to live in seconds,
            "ResourceRecords": [
              {
                "Value": "applicable value for the record type"
              },
              {...}
            ],
            "HealthCheckId": "optional ID of an Amazon Route 53 health check"
          }
        },
        {...}
      ]
    }
  }

**Weighted Alias Syntax**::

  {
    "ChangeBatch":
    {
      "Comment": "optional comment about the changes in this change batch request",
      "Changes": [
        {
          "Action": "CREATE"|"DELETE"|"UPSERT",
          "ResourceRecordSet": {
            "Name": "DNS domain name",
            "Type": "SOA"|"A"|"TXT"|"NS"|"CNAME"|"MX"|"PTR"|"SRV"|"SPF"|"AAAA",
            "SetIdentifier": "unique description for this resource record set",
            "Weight": value between 0 and 255,
            "AliasTarget": {
              "HostedZoneId": "hosted zone ID for your AWS resource",
              "DNSName": "DNS domain name for your AWS resource or for another resource record set in this hosted zone",
              "EvaluateTargetHealth": true|false
            },
            "HealthCheckId": "optional ID of an Amazon Route 53 health check"
          }
        },
        {...}
      ]
    }
  }