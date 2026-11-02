**To delete a policy**

The following ``delete-policy`` example deletes a policy from an organization. The example assumes that you previously detached the policy from all entities. ::

    aws organizations delete-policy \
        --policy-id p-examplepolicyid111

This command produces no output.

For more information, see `Deleting organization policies with AWS Organizations <https://docs.aws.amazon.com/organizations/latest/userguide/orgs_policies_delete.html>`__ in the *AWS Organizations User Guide*.
