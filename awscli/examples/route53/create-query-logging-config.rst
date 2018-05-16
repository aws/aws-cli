**To create a query logging configuration for DNS query logging**

You must create a CloudWatch log group and a resource policy for the log group before you can create a query logging configuration. For more information, see the following documentation.

* CloudWatch Logs `create-log-group`_command

.. _`create-log-group`: https://docs.aws.amazon.com/cli/latest/reference/logs/create-log-group.html

* CloudWatch Logs `put-resource-policy`_ command

.. _`put-resource-policy`: http://docs.aws.amazon.com/cli/latest/reference/logs/put-resource-policy.html
  
The following ``create-query-logging-config`` command creates a configuration for DNS query logging::

  aws route53 create-query-logging-config --hosted-zone-id --cloud-watch-logs-log-group-arn arn:aws:logs:us-east-2:123456789012:log-group:/aws/route53/example.com:*

You can also use the Route 53 console to create a query logging configuration. The console guides you through choosing an existing log group and, if necessary, guides you through creating a new resource policy. For more information, see `Logging DNS Queries`_ in the *Amazon Route 53 Developer Guide*.

.. _`Logging DNS Queries`: https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/query-logs.html
