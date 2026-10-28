**To delete an OU**

The following ``delete-organizational-unit`` example deletes an OU. The example assumes that you previously removed all accounts and other OUs from the OU. This command produces no output. ::

    aws organizations delete-organizational-unit \
        --organizational-unit-id ou-examplerootid111-exampleouid111
