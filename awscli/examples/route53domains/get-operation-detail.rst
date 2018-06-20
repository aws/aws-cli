**To get the current status of an operation**

The following ``get-operation-detail`` command returns the status of the operation that has an ``operation-id`` of ``edbd8d63-7fe7-4343-9bc5-54033EXAMPLE``::

  aws route53domains get-operation-detail --region us-east-1 --operation-id edbd8d63-7fe7-4343-9bc5-54033EXAMPLE
  
If the default region is us-east-1, you can omit the ``region`` parameter.