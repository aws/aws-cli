**To get information about a custom domain name**

Command::

  aws apigateway get-domain-name --domain-name api.domain.tld --region us-west-2

Output::

  {
      "domainName": "api.domain.tld", 
      "distributionDomainName": "d1a2f3a4c5o6d.cloudfront.net", 
      "certificateName": "uploadedCertificate", 
      "certificateUploadDate": 1462565487
  }

