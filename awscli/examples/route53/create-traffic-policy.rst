**To create a traffic policy**

The following ``create-traffic-policy`` command creates a traffic policy::

  aws route53 create-traffic-policy --name "example traffic policy" --document file://c:\temp\traffic-policy-doc.txt

For more information about the format of the document, see `Traffic Policy Document Format`_ in the *Amazon Route 53 API Reference*.

.. _`Traffic Policy Document Format`: http://docs.aws.amazon.com/Route53/latest/APIReference/api-policies-traffic-policy-document-format.html
  
You can also use the Route 53 console to create a traffic policy. For more information, see `Using Traffic Flow to Route DNS Traffic`_ in the *Amazon Route 53 Developer Guide*.

.. _`Using Traffic Flow to Route DNS Traffic`: http://docs.aws.amazon.com/Route53/latest/DeveloperGuide/traffic-flow.html
