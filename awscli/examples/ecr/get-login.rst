**To retrieve a Docker login command to your default registry**

This example prints a command that you can use to log in to your default Amazon
ECR registry.

Command::

  aws ecr get-login

Output::

  docker login -u AWS -p <password> -e none https://<aws_account_id>.dkr.ecr.<region>.amazonaws.com

**To log in to another account's registry**

This example prints one or more commands that you can use to log in to
Amazon ECR registries associated with other accounts.

Command::

  aws ecr get-login --registry-ids 012345678910 023456789012

Output::

  docker login -u <username> -p <token-1> -e none <endpoint-1>
  docker login -u <username> -p <token-2> -e none <endpoint-2>
