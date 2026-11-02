**To list resource policies for a response plan**

The following ``get-resource-policies`` example lists the resource policies associated with the specified response plan. ::

    aws ssm-incidents get-resource-policies \
        --resource-arn "arn:aws:ssm-incidents::123456789111:response-plan/Example-Response-Plan"

Output::

    {
        "resourcePolicies": [
            {
                "policyDocument": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Sid\":\"d901b37a-dbb0-458a-8842-75575c464219-external-principals\",\"Effect\":\"Allow\",\"Principal\":{\"AWS\":\"arn:aws:iam::123456789222:root\"},\"Action\":[\"ssm-incidents:GetResponsePlan\",\"ssm-incidents:StartIncident\",\"ssm-incidents:UpdateIncidentRecord\",\"ssm-incidents:GetIncidentRecord\",\"ssm-incidents:CreateTimelineEvent\",\"ssm-incidents:UpdateTimelineEvent\",\"ssm-incidents:GetTimelineEvent\",\"ssm-incidents:ListTimelineEvents\",\"ssm-incidents:UpdateRelatedItems\",\"ssm-incidents:ListRelatedItems\"],\"Resource\":[\"arn:aws:ssm-incidents:*:123456789111:response-plan/Example-Response-Plan\",\"arn:aws:ssm-incidents:*:123456789111:incident-record/Example-Response-Plan/*\"]}]}",
                "policyId": "be8b57191f0371f1c6827341aa3f0a03",
                "ramResourceShareRegion": "us-west-2"
            }
        ]
    }

For more information, see `Working with shared contacts and response plans <https://docs.aws.amazon.com/incident-manager/latest/userguide/sharing.html>`__ in the *Incident Manager User Guide*.