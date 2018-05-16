**To list authorizations for the AWS account that created a specified VPC to submit an associate-vpc-with-hosted-zone request**

The following ``list-vpc-association-authorizations`` command gets a list of the VPCs that were created by other accounts and that can be associated with a specified hosted zone because you've submitted one or more ``CreateVPCAssociationAuthorization`` requests. In this example, the private hosted zone has a ``hosted-zone-id`` of ``Z2MH303EXAMPLE``::

  aws route53 list-vpc-association-authorizations --hosted-zone-id Z2MH303EXAMPLE
  
  
