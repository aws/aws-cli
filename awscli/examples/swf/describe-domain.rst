**To get information about a domain**

The following ``describe-domain`` example gets detailed information about a particular domain. There is one required parameter:
``--name``, which takes the name of the domain you want information
about. ::

    aws swf describe-domain \
        --name DataFrobotz

Output::

    {
        "domainInfo": {
            "status": "REGISTERED",
            "name": "DataFrobotz"
        },
        "configuration": {
            "workflowExecutionRetentionPeriodInDays": "1"
        }
    }

You can also use ``describe-domain`` to get information about deprecated
domains. ::

    aws swf describe-domain \
        --name MyNeatNewDomain

Output::

    {
        "domainInfo": {
            "status": "DEPRECATED",
            "name": "MyNeatNewDomain"
        },
        "configuration": {
            "workflowExecutionRetentionPeriodInDays": "0"
        }
    }

For more information, see `Domains in Amazon SWF <https://docs.aws.amazon.com/amazonswf/latest/developerguide/swf-dev-domains.html>`__ in the *Amazon Simple Workflow Service Developer Guide*.
