**To list the status of operations that were performed on domains that are registered with the current AWS account**

The following ``list-operations`` command lists summary information, including the status, about the first 20 domain-registration operations that you performed using the current AWS account::

  aws route53domains list-operations --region us-east-1

If you have performed more than 100 operations (the maximum that you can list at a time), or if you want to list operations in groups of between 1 and 100, include the ``--maxitems`` parameter. For example, to list operations one at a time, use the following command::

  aws route53domains list-operations --region us-east-1 --max-items 1

To view information about the next operation, take the value of ``NextToken`` from the response to the preceding command, and include it in the ``--starting-token`` parameter, for example::

  aws route53domains list-operations --region us-east-1 --max-items 1 --starting-token eyJNYXJrZXIiOiBudWxsLCAiYm90b190cnVuY2F0ZV9hbW91bnQEXAMPLE==
  
If you want to list only the operations that were performed on or after a specified date, include the --submitted-since parameter. The date is in Coordinated Universal Time (UTC) and Unix time format. The following command lists operations that were performed on or after June 4, 2018 at 8 am UTC::

  aws route53domains list-operations --region us-east-1 --submitted-since 1528099200

If the default region is us-east-1, you can omit the ``region`` parameter.