**To associate an Amazon VPC with a private hosted zone**

The following ``associate-vpc-with-hosted-zone`` command associates an Amazon VPC with the Amazon Route 53 private hosted zone that has a ``hosted-zone-id`` of ``Z2MH303EXAMPLE``. The command uses the settings in the JSON-formatted file ``C:\temp\associate-vpc-with-hosted-zone.json``::

  aws route53 associate-vpc-with-hosted-zone --hosted-zone-id Z2MH303EXAMPLE --cli-input-json file://C:\temp\associate-vpc-with-hosted-zone.json

For more information, see `Associating More Amazon VPCs with a Private Hosted Zone`_ in the *Amazon Route 53 Developer Guide*.

.. _`Associating More Amazon VPCs with a Private Hosted Zone`: http://docs.aws.amazon.com/Route53/latest/DeveloperGuide/hosted-zone-private-associate-vpcs.html

Use the following syntax for associate-vpc-with-hosted-zone.json::

  {
    "Comment": "string",
    "VPC": {
	  "VPCId": "string",
	  "VPCRegion": "string"
	}
  }