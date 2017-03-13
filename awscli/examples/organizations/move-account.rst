**To move an account to a different OU or root**

The following example shows how to move a member account from the root to an OU.  

Command::

  aws organizations move-account --account-id 333333333333 --source-parent-id r-examplerootid111 --destination-parent-id ou-examplerootid111-exampleouid111