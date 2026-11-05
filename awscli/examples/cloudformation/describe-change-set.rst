**To get information about a change set**

The following ``describe-change-set`` example displays the details of the change set specified by change set name and stack name. ::

    aws cloudformation describe-change-set \
        --change-set-name my-change-set \
        --stack-name my-stack

The following ``describe-change-set`` example displays the details of the change set specified by the full ARN of the change set. ::

    aws cloudformation describe-change-set \
        --change-set-name arn:aws:cloudformation:us-west-2:123456789012:changeSet/my-change-set/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "Changes": [
            {
                "Type": "Resource",
                "ResourceChange": {
                    "Action": "Modify",
                    "LogicalResourceId": "function",
                    "PhysicalResourceId": "my-function-SEZV4XMPL4S5",
                    "ResourceType": "AWS::Lambda::Function",
                    "Replacement": "False",
                    "Scope": [
                        "Properties"
                    ],
                    "Details": [
                        {
                            "Target": {
                                "Attribute": "Properties",
                                "Name": "Timeout",
                                "RequiresRecreation": "Never"
                            },
                            "Evaluation": "Static",
                            "ChangeSource": "DirectModification"
                        }
                    ]
                }
            }
        ],
        "ChangeSetName": "my-change-set",
        "ChangeSetId": "arn:aws:cloudformation:us-west-2:123456789012:changeSet/my-change-set/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "StackId": "arn:aws:cloudformation:us-west-2:123456789012:stack/my-stack/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "StackName": "my-stack",
        "Description": null,
        "Parameters": null,
        "CreationTime": "2019-10-02T05:20:56.651Z",
        "ExecutionStatus": "AVAILABLE",
        "Status": "CREATE_COMPLETE",
        "StatusReason": null,
        "NotificationARNs": [],
        "RollbackConfiguration": {},
        "Capabilities": [
            "CAPABILITY_IAM"
        ],
        "Tags": null
    }

For more information, see `View a change set for a CloudFormation stack <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-changesets-view.html>`__ in the *AWS CloudFormation User Guide*.
