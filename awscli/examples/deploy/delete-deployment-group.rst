**To delete a deployment group**

The following ``delete-deployment-group`` example deletes a deployment group that is associated with the specified application. ::

    aws deploy delete-deployment-group \
        --application-name WordPress_App \
        --deployment-group-name WordPress_DG

Output::

    {
        "hooksNotCleanedUp": []
    }

For more information, see `Delete a deployment group with CodeDeploy <https://docs.aws.amazon.com/codedeploy/latest/userguide/deployment-groups-delete.html>`__ in the *AWS CodeDeploy User Guide*.
