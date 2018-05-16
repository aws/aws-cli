**To authorize the AWS account that created a specified VPC to submit an associate-vpc-with-hosted-zone request**

The following ``create-vpc-association-authorization`` command authorizes the AWS account that created a specified VPC to submit an ``associate-vpc-with-hosted-zone`` request. To submit a ``create-vpc-association-authorization`` request, you must use the account that created the hosted zone. In this example, the private hosted zone has a ``hosted-zone-id`` of ``Z2MH303EXAMPLE``. The command uses the settings in the JSON-formatted file ``C:\temp\create-vpc-association-authorization.json``::

  aws route53 create-vpc-association-authorization --hosted-zone-id Z2MH303EXAMPLE --cli-input-json file://C:\temp\create-vpc-association-authorization.json

For more information, see `Associating an Amazon VPC and a Private Hosted Zone That You Created with Different AWS Accounts`_ in the *Amazon Route 53 Developer Guide*.

.. _`Associating an Amazon VPC and a Private Hosted Zone That You Created with Different AWS Accounts `: http://docs.aws.amazon.com/Route53/latest/DeveloperGuide/hosted-zone-private-associate-vpcs-different-accounts.html

Use the following syntax for ``create-vpc-association-authorization.json``::

  {
    "VPC": {
	  "VPCId": "string",
	  "VPCRegion": "string"
	}
  }
