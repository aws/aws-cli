**To retrieve a list of all of the child accounts and OUs in a parent root or OU**

The following example shows how to request a list of all of the child OUs in a parent root or OU.  

Command::

  aws organizations list-children --child-type ORGANIZATIONAL_UNIT --parent-id ou-examplerootid111-exampleouid111
  
Output::
  {
    "Children": [
      {
        "Id": "ou-examplerootid111-exampleouid111",
        "Type": "ORGANIZATIONAL_UNIT"
      },
      {
        "Id": "ou-examplerootid111-exampleouid222",
        "Type":"ORGANIZATIONAL_UNIT"
      }
    ]
  }