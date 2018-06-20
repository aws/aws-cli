**To list query logging configurations**

The following ``list-query-logging-configs`` command lists information about the first 100 query logging configurations that are associated with the current AWS account.::

  aws route53 list-query-logging-configs

The following command lists the query logging configurations for the specified hosted zone::

  aws route53 list-query-logging-configs --hosted-zone-id Z1OX3WQEXAMPLE
  
If you have more than 100 query logging configurations, or if you want to list them in groups smaller than 100, include the ``--maxitems`` parameter. For example, to list query logging configurations one at a time, use the following command::

  aws route53 list-query-logging-configs --max-items 1

To view the next query logging configuration, take the value of ``NextToken`` from the response to the previous command, and include it in the ``--next-token`` parameter, for example::

  aws route53 list-query-logging-configs --max-items 1 --next-token 02ec8401-9879-4259-91fa-09467EXAMPLE