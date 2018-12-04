**To describe an image**

This example describes an image with the tag ``precise`` in a repository called
``ubuntu`` in the default registry for an account.

Command::

  aws ecr batch-get-image --repository-name ubuntu --image-ids imageTag=precise
