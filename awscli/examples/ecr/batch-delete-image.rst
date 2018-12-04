**To delete an image**

This example deletes an image with the tag ``precise`` in a repository called
``ubuntu`` in the default registry for an account.

Command::

  aws ecr batch-delete-image --repository-name ubuntu --image-ids imageTag=precise

Output::

  {
      "failures": [],
      "imageIds": [
          {
              "imageTag": "precise",
              "imageDigest": "sha256:19665f1e6d1e504117a1743c0a3d3753086354a38375961f2e665416ef4b1b2f"
          }
      ]
  }
