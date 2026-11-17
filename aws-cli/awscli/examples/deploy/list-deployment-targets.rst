**To retrieve a list of target IDs that are associated with a deployment**

The following ``list-deployment-targets`` example retrieves a list of target IDs associated with deployments that have a status of "Failed" or "InProgress". ::

    aws deploy list-deployment-targets \
        --deployment-id "d-A1B2C3111" \
        --target-filters "{\"TargetStatus\":[\"Failed\",\"InProgress\"]}"

Output::

    {
        "targetIds": [
            "i-0f1558aaf90e5f1f9"
        ]
    }

For more information, see `View instance details with CodeDeploy <https://docs.aws.amazon.com/codedeploy/latest/userguide/instances-view-details.html>`__ in the *AWS CodeDeploy User Guide*.
