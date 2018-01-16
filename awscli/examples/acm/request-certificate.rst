**To request a new ACM certificate**

The following ``request-certificate`` command requests a new certificate for the www.example.com domain using DNS validation::

  aws acm request-certificate --domain-name www.example.com --validation-method DNS  

You can enter an idempotency token to distinguish between calls to ``request-certificate``::

  aws acm request-certificate --domain-name www.example.com --validation-method DNS --idempotency-token 91adc45q

You can enter an alternative name that can be used to reach your website::

  aws acm request-certificate --domain-name www.example.com --validation-method DNS --idempotency-token 91adc45q --subject-alternative-names www.example.net

You can also enter multiple alternative names::

  aws acm request-certificate --domain-name a.example.com --validation-method DNS --subject-alternative-names b.example.com c.example.com d.example.com *.e.example.com *.f.example.com

You can also enter domain validation options to specify the domain to which validation email will be sent::

  aws acm request-certificate --domain-name example.com --validation-method DNS --subject-alternative-names www.example.com --domain-validation-options DomainName=www.example.com,ValidationDomain=example.com
