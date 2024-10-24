**To retrieve the code binding source URI from an existing schema version for a particular language and exports the content to an outfile**

The following ``get-code-binding-source`` retrieves the code binding source URI from an existing schema version for a particular language and exports the content to an outfile. You may specify languages such as Java8, TypeScript3, Python36, and Go1. If successful, your code binding source URI will be available in your local machine. This command produces no output. ::

	aws schemas get-code-binding-source \
		--registry-name example-registry \ 
		--schema-name example-schema \
		--language Python36 <outfile>.zip 

For more information, see `Amazon EventBridge schemas <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html>`__ in the *Amazon EventBridge User Guide*.