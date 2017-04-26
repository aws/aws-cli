**To list all the parents of a child OU or account**

The following example shows how to list the root or OUs that contain account 444444444444.  

Command::

  aws organizations list-parents --child-id 444444444444

Output::

  {
    "Parents": [
      {
        "Id": "ou-examplerootid111-exampleouid111",
        "Type": "ORGANIZATIONAL_UNIT"
      }
    ]
  }