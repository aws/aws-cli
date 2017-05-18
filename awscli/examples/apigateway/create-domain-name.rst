**To create the custom domain name**

Command::

  aws apigateway create-domain-name --domain-name 'my.domain.tld' --certificate-name 'my.domain.tld cert' --certificate-body '<cert here>' --certificate-private-key '<cert key here>' --certificate-chain '<cert chain here>'
