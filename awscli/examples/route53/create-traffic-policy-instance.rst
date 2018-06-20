**To create records in a hosted zone based on a traffic policy version**

The following ``create-traffic-policy-instance`` command creates records in a hosted zone based on a specified version of a traffic policy::

  aws route53 create-traffic-policy-instance --hosted-zone-id Z1D6337EXAMPLE --name cli-test.example.com --ttl 300 --traffic-policy-id 2d826c42-c6c8-4679-893f-28351EXAMPLE --traffic-policy-version 3

For more information about traffic policies and traffic policy instances (called traffic policy records in the Route 53 console), see `Using Traffic Flow to Route DNS Traffic`_ in the *Amazon Route 53 Developer Guide*.

.. _`Using Traffic Flow to Route DNS Traffic`: http://docs.aws.amazon.com/Route53/latest/DeveloperGuide/traffic-flow.html
