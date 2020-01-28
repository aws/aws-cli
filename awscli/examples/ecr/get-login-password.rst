**To retrieve a password to your default registry**

This example prints a password that you can use with a container client of your
choice to log in to your default Amazon ECR registry.

Command::

  aws ecr get-login-password

Output::

  <password>

Usage with Docker::

  aws ecr get-login-password | docker login --username AWS --password-stdin https://<aws_account_id>.dkr.ecr.<region>.amazonaws.com
