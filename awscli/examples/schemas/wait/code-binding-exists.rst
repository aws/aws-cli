**To wait for a new code binding to be created from the put-code-binding API**

The following ``update-registry`` will wait for a new code binding to be created from the put-code-binding API. If the command succeeds, no output is returned. ::

	aws schemas wait code-binding-exists \
		--registry-name example-registry \
		--schema-name example-schema \
		--schema-version 6 \
		--language Python36