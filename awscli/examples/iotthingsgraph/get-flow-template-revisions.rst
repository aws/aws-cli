**To get revision information about a flow**

The following ``get-flow-template-revisions`` example gets revision information about a flow (workflow). ::

    aws iotthingsgraph get-flow-template-revisions \
        --id urn:tdm:us-west-2/123456789012/default:Workflow:MyFlow

Output::

    {
        "summaries": [
            {
                "id": "urn:tdm:us-west-2/123456789012/default:Workflow:MyFlow",
                "revisionNumber": 1,
                "createdAt": 1559247540.292
            }
        ]
    }
