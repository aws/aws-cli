**To delete a list of parameters**

This example deletes a list of parameters.

Command::

  aws ssm delete-parameters --names "HelloWorld" "GoodbyeWorld"

Output::

  {
    "DeletedParameters": [
        "HelloWorld",
        "GoodbyeWorld"
    ],
    "InvalidParameters": []
  }