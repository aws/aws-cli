**To create a public hosted zone**

The following ``create-hosted-zone`` command adds a public hosted zone named ``example.com`` using the caller reference ``2018-06-01-18:47``. The optional comment includes a space, so it must be enclosed in quotation marks::

  aws route53 create-hosted-zone --name example.com --caller-reference 2018-06-01-18:47 --hosted-zone-config Comment="sample comment"

For more information, see `Working with Hosted Zones`_ in the *Amazon Route 53 Developer Guide*.

.. _`Working with Hosted Zones`: http://docs.aws.amazon.com/Route53/latest/DeveloperGuide/AboutHZWorkingWith.html

**To create a private hosted zone**

The following ``create-hosted-zone`` command created a private hosted zone using the values in the JSON-formatted document create-hosted-zone-private.json::

  aws route53 create-hosted-zone --cli-input-json file://c:\temp\create-hosted-zone-private.json

create-hosted-zone-private.json::

  {
      "CallerReference": "2018-06-01-18:47",
      "HostedZoneConfig": {
          "Comment": "for test system",
          "PrivateZone": true
      },
      "Name": "cli-private-hosted-zone-test",
      "VPC": {
          "VPCId": "vpc-12345678",
          "VPCRegion": "us-west-1"
      }
  }
  
For more information, see `Working with Hosted Zones`_ in the *Amazon Route 53 Developer Guide*.

.. _`Working with Hosted Zones`: http://docs.aws.amazon.com/Route53/latest/DeveloperGuide/AboutHZWorkingWith.html
