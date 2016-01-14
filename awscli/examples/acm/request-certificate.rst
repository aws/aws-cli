**To request a new ACM certificate**

The following ``request-certificate`` command requests a new certificate for the www.example.com domain::

  aws acm request-certificate --domain-name www.example.com

You can enter an idempotency token to distinguish between calls to ``request-certificate``::

  aws acm request-certificate --domain-name www.example.com --idempotency-token 91adc45q

You can enter one or more alternative names that can be used to reach your website::

  aws acm request-certificate --domain-name www.example.com --idempotency-token 91adc45q --subject-alternative-names www.example.net

You can also enter domain validation options to specify the domain to which validation email will be sent::

  aws acm request-certificate --domain-name example.com --subject-alternative-names www.example.com --domain-validation-options DomainName=www.example.com,ValidationDomain=example.com
