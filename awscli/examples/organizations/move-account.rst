**To move an account between roots or OUs**

The following ``move-account`` example moves the management account in the organization from the root to an OU. ::

    aws organizations move-account \
        --account-id 123456789222 \
        --source-parent-id r-examplerootid111 \
        --destination-parent-id ou-examplerootid111-exampleouid111

This command produces no output.

For more information, see `Moving accounts to an organizational unit (OU) or between the root and OUs with AWS Organizations <https://docs.aws.amazon.com/organizations/latest/userguide/move_account_to_ou.html>`__ in the *AWS Organizations User Guide*.
