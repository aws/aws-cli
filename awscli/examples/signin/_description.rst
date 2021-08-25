Generate a sign-in URL for the AWS Management Console using temporary
credentials.

This command **MUST** be invoked with a profile containing temporary credentials. The profile may not contain long-term credentials including **aws_access_key_id** and **aws_secret_access_key**.

This command is used to provide AWS Management Console access to a set of assumed role credentials. A typical workflow allows for a AWS IAM User without direct console access to assume a role, then run this **signin** command to generate a URL allowing sign-in to the AWS Management Console. Typically this command will be used when an AWS IAM User has an Access Key and Secret Access Key, no console login password, but access to assume a role.

The following credential configuration also allows for transparent role assumption::

  [my_user]
  aws_access_key_id = AKIAABCDEFGHIJKLMNOP
  aws_secret_access_key = ...

  [default]
  role_arn = arn:aws:iam::012345678910:role/my_role
  role_session_name = example-session-name
  source_profile = my_user
  duration_seconds = 43200

For more information on this process, see `Enabling custom identity broker access to the AWS console`_ in the *AWS Identity and Access Management User Guide*.

.. _`Enabling custom identity broker access to the AWS console`: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_enable-console-custom-url.html
