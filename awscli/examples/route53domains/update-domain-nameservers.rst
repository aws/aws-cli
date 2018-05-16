**To update the name servers for a domain**

The following ``update-domain-nameservers`` command updates the name servers for a domain using the settings in the JSON-formatted file ``C:\temp\update-domain-nameservers.json``::

  aws route53 update-domain-nameservers --region us-east-1 --cli-input-json file://C:\temp\update-domain-nameservers.json

If the default region is us-east-1, you can omit the ``region`` parameter.

For more information, see `Adding or Changing Name Servers and Glue Records for a Domain`_ in the *Amazon Route 53 Developer Guide*.

.. _`Adding or Changing Name Servers and Glue Records for a Domain`: http://docs.aws.amazon.com/Route53/latest/DeveloperGuide/domain-name-servers-glue-records.html

Use the following syntax for update-domain-nameservers.json::

  {
    "DomainName": "string",
    "FIAuthKey": "string",
    "Nameservers": [ 
      { 
        "GlueIps": [ "string" ],
        "Name": "string"
      }
    ]
  }