**To deprecate a domain**

The following ``deprecate-domain`` example deprecates a domain. You can still see a deprecated domain, but cannot create new workflow executions or register types on it. The command has a sole required parameter, ``--name``, which takes the name of the domain to deprecate. ::

    aws swf deprecate-domain \
        --name MyNeatNewDomain

This command produces no output.

As with ``register-domain``, no output is returned. If you use
``list-domains`` to view the registered domains, however, you will see
that the domain has been deprecated and no longer appears in the
returned data. ::

    aws swf list-domains \
        --registration-status REGISTERED

Output::

    {
        "domainInfos": [
            {
                "status": "REGISTERED",
                "name": "DataFrobotz"
            },
            {
                "status": "REGISTERED",
                "name": "erontest"
            }
        ]
    }

If you use ``--registration-status DEPRECATED`` with ``list-domains``, you will see your deprecated domain. ::

    aws swf list-domains \
        --registration-status DEPRECATED

Output::

    {
        "domainInfos": [
            {
                "status": "DEPRECATED",
                "name": "MyNeatNewDomain"
            }
        ]
    }

You can still use ``describe-domain`` to get information about a deprecated domain. ::

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
