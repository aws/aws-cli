**To get details of a response plan**

The following ``get-response-plan`` example gets details about a specified response plan in your AWS account. ::

    aws ssm-incidents get-response-plan \
        --arn "arn:aws:ssm-incidents::123456789012:response-plan/Example-Response-Plan"

Output::

    {
        "actions": [
            {
                "ssmAutomation": {
                    "documentName": "AWSIncidents-CriticalIncidentRunbookTemplate",
                    "documentVersion": "$DEFAULT",
                    "roleArn": "arn:aws:iam::123456789012:role/aws-service-role/ssm-incidents.amazonaws.com/AWSServiceRoleForIncidentManager",
                    "targetAccount": "RESPONSE_PLAN_OWNER_ACCOUNT"
                }
            }
        ],
        "arn": "arn:aws:ssm-incidents::123456789012:response-plan/Example-Response-Plan",
        "chatChannel": {
            "chatbotSns": [
                "arn:aws:sns:us-west-2:123456789012:Standard_User"
            ]
        },
        "displayName": "Example response plan",
        "engagements": [
            "arn:aws:ssm-contacts:us-west-2:123456789012:contact/example"
        ],
        "incidentTemplate": {
            "impact": 5,
            "title": "Example-Incident"
        },
        "name": "Example-Response-Plan"
    }

For more information, see `Incident preparation <https://docs.aws.amazon.com/incident-manager/latest/userguide/incident-response.html>`__ in the *Incident Manager User Guide*.