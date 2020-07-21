**To generate a random password**

The following example shows how to request a randomly generated password. This example includes the optional flags to require spaces and at least one character of each included type. It specifies a length of 20 characters. ::

	aws secretsmanager get-random-password --include-space --password-length 20 --require-each-included-type 

The output shows the following: ::

	{
	  "RandomPassword": "N+Z43a,>vx7j O8^*<8i3"
	}
