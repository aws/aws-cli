**To update the description for a resource group**

This example updates the description for a group named WebServer3 in the current region.

Command::

  aws resource-groups update-group --group-name WebServer3 --description "Group of web server resources."

Output::

  {
    "Group": {
        "GroupArn": "arn:aws:resource-groups:us-east-2:000000000000:group/WebServer3",
        "Name": "WebServer3"
		"Description": "Group of web server resources."
    }
}


