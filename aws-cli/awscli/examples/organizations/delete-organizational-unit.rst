**To delete an OU**

The following ``delete-organizational-unit`` example deletes an OU. The example assumes that you previously removed all accounts and other OUs from the OU. ::

    aws organizations delete-organizational-unit \
        --organizational-unit-id ou-examplerootid111-exampleouid111

This command produces no output.

For more information, see `Deleting an organizational unit (OU) with AWS Organizations <https://docs.aws.amazon.com/organizations/latest/userguide/delete-ou.html>`__ in the *AWS Organizations User Guide*.
