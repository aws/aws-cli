**To get an authorization token for your default registry**

This example command gets an authorization token for your default registry.

Command::

  aws ecr get-authorization-token

Output::

  {
      "authorizationData": [
          {
              "authorizationToken": "QVdTOkN...",
              "expiresAt": 1448875853.241,
              "proxyEndpoint": "https://<aws_account_id>.dkr.ecr.us-west-2.amazonaws.com"
          }
      ]
  }


**To get the decoded password for your default registry**

This example command gets an authorization token for your default registry and
returns the decoded password for you to use in a ``docker login`` command.

.. note::

    Mac OSX users should use the ``-D`` option to ``base64`` to decode the
    token data.

Command::

  aws ecr get-authorization-token --output text \
  --query 'authorizationData[].authorizationToken' \
  | base64 -D | cut -d: -f2


**To `docker login` with your decoded password**

This example command uses your decoded password to add authentication
information to your Docker installation by using the ``docker login`` command.
The user name is ``AWS``, and you can use any email you want (Amazon ECR does
nothing with this information, but ``docker login`` required the email field).

.. note::

    The final argument is the ``proxyEndpoint`` returned from
    ``get-authorization-token`` without the ``https://`` prefix.

Command::

  docker login -u AWS -p <my_decoded_password> -e <any_email_address> <aws_account_id>.dkr.ecr.us-west-2.amazonaws.com

Output::

  WARNING: login credentials saved in $HOME/.docker/config.json
  Login Succeeded
