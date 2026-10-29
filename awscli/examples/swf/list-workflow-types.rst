**To list workflow types**

The following ``list-workflow-types`` example gets a list of the workflow types for a domain. The ``--domain`` and
``--registration-status`` arguments are required. ::

    aws swf list-workflow-types \
        --domain DataFrobtzz \
        --registration-status REGISTERED

Output::

    {
        "typeInfos": [
            {
                "status": "REGISTERED",
                "creationDate": 1371454149.598,
                "description": "DataFrobtzz subscribe workflow",
                "workflowType": {
                    "version": "v3",
                    "name": "subscribe"
                }
            }
        ]
    }

As with ``list-activity-types``, you can use the ``--name`` argument to select only workflow types with a particular name, and use the ``--maximum-page-size`` argument in coordination with ``--next-page-token`` to page results. To reverse the order in which results are returned, use ``--reverse-order``.

For more information, see `Basic workflow concepts in Amazon SWF <https://docs.aws.amazon.com/amazonswf/latest/developerguide/swf-dg-basic.html>`__ in the *Amazon Simple Workflow Service Developer Guide*.
