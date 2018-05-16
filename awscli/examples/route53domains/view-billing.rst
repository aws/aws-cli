**To get billing information for domain registration charges for the current AWS account**

The following ``view-billing`` command returns billing information for domain registration charges during a specified time period. The command uses the settings in the JSON-formatted file ``C:\temp\view-billing.json``::

  aws route53 view-billing --region us-east-1 --cli-input-json file://C:\temp\view-billing.json

The beginning date (Start) and ending date (End) for the time period are in Coordinated Universal Time (UTC) and Unix time format.
  
If the default region is us-east-1, you can omit the ``region`` parameter.

For more information, see `ViewBilling`_ in the *Amazon Route 53 API Reference*.

.. _`ViewBilling`: http://docs.aws.amazon.com/Route53/latest/APIReference/API_domains_ViewBilling.html

Use the following syntax for view-billing.json::

  {
    "End": number,
    "Marker": "string",
    "MaxItems": number,
    "Start": number
  }