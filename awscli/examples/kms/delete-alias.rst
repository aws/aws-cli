**To delete an AWS KMS alias**

The following ``delete-alias`` example deletes the alias ``alias/example-alias``. 

* The ``--alias-name`` parameter specifies the alias to delete. The alias name must begin with `alias/`. ::

    aws kms delete-alias \
        --alias-name alias/example-alias

This command produces no output. To find the alias, use the ``list-aliases`` command.

For more information, see `Working with Aliases <https://docs.aws.amazon.com/kms/latest/developerguide/programming-aliases.html>`__ in the *AWS Key Management Service Developer Guide*.
