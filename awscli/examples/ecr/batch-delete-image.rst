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

This example deletes multiple images by the ``SHA256`` hash in a repository called
``ubuntu`` in the default registry for an account.

Command::

  aws ecr batch-delete-image --repository-name ubuntu imageDigest=sha256:71b0c3f03a0ea8dc79f2853a6f4a66d632257e781d263f6951c2aa8c4f1a3078 imageDigest=sha256:c598f629ab6255397795fda45947161b05ce5a94eae592762436cac3f71f7812

Output::

  {
      "failures": [],
      "imageIds": [
          {
              "imageTag": "b70634b",
              "imageDigest": "sha256:c598f629ab6255397795fda45947161b05ce5a94eae592762436cac3f71f7812"
          },
          {
              "imageTag": "9ab868e",
              "imageDigest": "sha256:71b0c3f03a0ea8dc79f2853a6f4a66d632257e781d263f6951c2aa8c4f1a3078"
          }
      ]
  }
