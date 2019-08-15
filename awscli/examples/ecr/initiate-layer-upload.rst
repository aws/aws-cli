**To initiate an image layer upload**

This example initiates an image layer upload for the ``hello-world`` repository.

Command::

  aws ecr initiate-layer-upload --repository-name hello-world
  
Output::

  {
      "uploadId": "4eb64aee-14ee-aae4-1e94-6593c01b39f8",
      "partSize": 10485760
  }