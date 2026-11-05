**To update the trust policy of an IAM Role to be used with Amazon EMR on EKS**

The following ``update-role-trust-policy`` example updates the trust policy of a role named **example_iam_role** such that it can be used with Amazon EMR on EKS with
**example_namespace** namespace from an EKS cluster named **example_cluster**. ::

    aws emr-containers update-role-trust-policy \
        --cluster example_cluster \
        --namespace example_namespace \
        --role-name example_iam_role

If the trust policy has already been updated, the command displays the following output.

Output::

    Trust policy statement already exists for role example_iam_role. No changes were made!

If the trust policy has not been updated yet, the command displays the following output.

Output::

    Successfully updated trust policy of role example_iam_role.

For more information, see `Update the trust policy of the job execution role <https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/setting-up-trust-policy.html>`__ in the *Amazon EMR on EKS Development Guide*.
