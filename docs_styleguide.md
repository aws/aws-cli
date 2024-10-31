# AWS CLI code example style guide

```{danger}
The AWS CLI repository is a **public** GitHub repository and submitting examples before a feature launch produces issues. You must be able to run the command from the public installation source.
```

This page outlines the code example guidelines for AWS Command Line Interface (AWS CLI) examples as part of the [contribution process](contribution_process.md). 

-----

## Before you start

* Create all examples using a plain text editor or code editor like Notepad, Notepad++, or VS Code. **Do not** use word processors like Word or Outlook. We suggest you use an editor where you can easily see whitespace.
* Always [sanitize sensitive information](docs_styleguide#sanitizing-sensitive-information) in your examples.

## Example file (template)

Download the `.rst` template: [command-name.zip](_static/files/command-name.zip)

For details on each part of the template, see the [style guide](#style-guide). The general format of your `.rst` file looks like the following:

```{admonition} command-name.rst
    **To list the available widgets**
    
    The following ``command-name`` example lists the available widgets in your AWS account. ::
    
        aws awesomeservice command-name \
            --parameter1 file://myfile.json \
            --parameter2 value2 \
            --lastparam lastvalue
    
    Contents of ``myfile.json``::
    
        {
            "somekey": "some value"
        }
    
    Output::
    
        {
            "All of the output": "goes here",
            "More Output": [
                { "arrayitem1": 1 },
                { "arrayitem2": 2 }
            ]
            "Each indent": "Must be 4 spaces"
        }
    
    For more information, see `This is the topic title <https://link.to.the/topic/page>`__ in the *Name of your guide*.
```

Some commands require multiple examples to cover typical use cases. To add multiple examples for one command, copy the template and paste it in the same file following the first example. Use a different title and description to distinguish between multiple examples.

## Style guide

### General

1. Confirm your examples are real working examples that others can copy/paste without needing major changes.
2. CLI examples must be formatted as [reStructured Text (reST)](https://devguide.python.org/documentation/markup/).
3. Examples must contain only [ASCII characters](https://en.wikipedia.org/wiki/ASCII), they cannot contain characters such as fancy quotes or tab indenting.
    ```
    a-z, 0-9, !"#$%&'()*+,-./\:;<=>?@[]^_`{}|
    ```
4. **Do not use tab indenting**. Indents should include *exactly* 4 spaces per level of indentation.
5. All examples for a command are in a singular `.rst` file. When contributing examples, confirm you are not unintentionally overwriting existing examples.
6. Examples should be formatted for Linux terminals. If you are formatting for another operating system, such as Windows, it must be listed in the title of the example.
7. To keep consistency across the AWS CLI examples, set your profile's output to `json` format. Do not explicitly include an `--output` parameter in the example unless you must show the output in a format that is not `json`.
8. Note down any AWS resources you might create for these examples. After you're done running commands for your examples, delete any testing resources that you created to avoid any unnecessary ongoing costs.
9. All sections of content must have blank lines separating them from other content:
    ```
    **To list users**
        
    The following ``list-users`` example lists users in the specified account ::
    ```

### Sanitizing sensitive information

Sanitize your examples. Replace all sensitive information with placeholders such as:

* **Account IDs:** 123456789012  
    If your example requires multiple account IDs, then use this pattern:  
    123456789***111***, 123456789***222***, 123456789***333***, ...
* **GUIDs:** a1b2c3d4-5678-90ab-cdef-EXAMPLE11111  
    If your example requires multiple GUIDs, then use this pattern:  
    **** a1b2c3d4-5678-90ab-cdef-EXAMPLE***22222***, a1b2c3d4-5678-90ab-cdef-EXAMPLE***33333***, ...
* **Regions:** us-west-2  
    Unless the resource can only exist in a different region.
* **Bucket names:** amzn-s3-demo-bucket  
    If your example requires multiple buckets, then use this pattern:  
    amzn-s3-demo-bucket**1**, amzn-s3-demo-bucket**2**, amzn-s3-demo-bucket**3,** ...

### Example file location

1. AWS CLI examples are located in the [`/aws-cli/awscli/examples`](https://github.com/aws/aws-cli/tree/develop/awscli/examples) folder in the repository. Services are organized by the command group name.  
    **Example:** The examples for the  `aws autoscaling-plans create-scaling-plan` command is located in the [`examples/autoscaling-plans`](https://github.com/aws/aws-cli/tree/develop/awscli/examples/autoscaling-plans) folder.
2. If there is no folder for the command service, create the folder named exactly after the command group and place your examples in it.
3. Examples for `wait` commands are in a command group’s subfolder named `wait`.  
    **Example:** The `aws ecs wait services-stable` will be in the [`examples/ec2/wait`](https://github.com/aws/aws-cli/tree/develop/awscli/examples/ec2/wait) folder.

### Filename

1. Name your file the exact name of your command, with the `.rst` extension.  
    **Example:** A command example of `list-user` must have a filename of `list-user.rst`
2. Examples for `wait` commands need a file for each sub-command.  
    **Example:** If your command is `aws ecs wait services-stable`, then you should have a file named `services-stable.rst`.

### Title

```{admonition} Example
    **To list users**
```

1. Format the title in the form of “`To do something`". You must surround the title with double asterisks with no spaces between the title and the asterisks.
2. If there is more than one example in the file, number each example in the title as follows.
    ```
    **Example 1: To do this one way**
    ```
    
    ```
    **Example 2: To do it another way**
    ```
3. Examples should be formatted for Linux terminals. If you are formatting for another operating system, such as Windows, it must be listed in the title of the example.
    `**To do it another way (Windows)**`

### Description

```{admonition} Example
    The following ``list-users`` example lists the users in the specified account. ::
```

1. The description must begin with the expression 
    ```
    The following ``command-name`` example ... 
    ```
2. Any time a command or parameter name is used, it must be surrounded by two back-tick characters ``` `` ``` at both the start and end.
3. Follow the initial phrase with an active verb describing what the command does and keep it simple and present tense.
4. Describe how the command helps the customer complete their scenario.
5. The description must end with a period, followed by a space and two colons `::`
7. **If any of your examples are for the "wait" command with a sub-command:** Modify the description with your sub-command name and a description of what it checks for.  
    **Example:**
    ```
    The following ``wait sub-command-name`` example pauses and resumes only after it can confirm that the specified table exists. ::
    ```    

### Command

```{admonition} Example
        aws awesomeservice command-name \
            --parameter1 file://myfile.json \
            --parameter2 value2 \
            --lastparam lastvalue
```

1. Provide your tested and working command example.
2. Examples should be formatted for Linux terminals. If you are formatting for another operating system, such as Windows, it must be listed in the title of the example.
3. Every line except the last must end with the Linux line continuation mark of a space and a backslash. The only exception is if you are documenting a command that runs only on an operating system that uses a different line continuation character.
4. The first line is the basic command indented 4 spaces.
5. Every parameter must be on its own line, indented 8 spaces, two dashes, the parameter name and the parameter value.
6. Use value and resource names that are more use-case oriented than "`username1`" or "`mytestbucket`" while still clearly indicating what it is. Use parameter names and values that are suitable for a scenario.
7. Do not use the `--output` parameter. Assume and use `json` output as the default unless it is critical to your example to use another style.
8. Do not use the `--region` parameter unless it is critical to this example. Most customers set a default region in their config file and then refer to it only when really required.

### File contents

```{admonition} Example
    Contents of ``myfile.json``::

        {
            "somekey": "some value"
        }
```

1. If you use a file in your example command, the contents of the file must be provided. This includes files referenced by `--cli-input-json`, `--cli-input-yaml` for all parameters, and the `file://` syntax for a single parameter.
2. The introduction line must be left aligned, with no leading spaces. The file name must have two back ticks ` `` ` preceding and following with no spaces. Add two colons immediately after the last back tick with no spaces.
    ```
    Contents of ``myfile.json``::
    ```
3. After a blank line, enter your file content, with all indentations preserved, but with each line indented an additional 4 spaces
4. There must be a “contents of” section for every file your command has.

### Output

There are two possible ways example command output is displayed:
1. Under normal circumstances the command produces **output**, sample output must be provided.
1. Under normal circumstances the command produces **no output**.

#### Command produces output

```{admonition} Example
    Output::

        {
            "All of the output": "goes here",
            "More Output": [
                { "arrayitem1": 1 },
                { "arrayitem2": 2 }
            ]
            "Each indent": "Must be 4 spaces"
        }
```

1. The output content must be a working example.
2. To keep consistency through out the CLI Reference examples, show the `json` version of the output. If it is critical to your example, you can show another output type. If you use an output type other than `json`, then include the `--output` parameter in your example command.
3. The header line must be left aligned, with no leading spaces, and two colons immediately after the last back tick with no spaces. `Output::`
4. Enter a blank line, and then paste your output, with each line indentation being an additional 4 spaces.
5. [Sanitize any relevant output](#sanitizing-sensitive-information).

#### Command produces no output

```{admonition} Example
    This command produces no output.
```

Do not include the `Output::` line and instead use the following to indicate that there is no output for this command.

```
This command produces no output.
```

### For more information link

```{admonition} Example
    For more information, see `This is the topic title <https://link.to.the/topic/page>`__ in the *Name of the guide*.
```

1. Every example must have at least one AWS link that points the user to more information about the concepts in the example. Link to a conceptual topic in the relevant User Guide or Developer Guide that explains the resource, the operation, or the general principle that the example demonstrates.
2. **Do not** link to the API reference for the command as it’s the same generated text as the CLI reference page.
3. The see more information sentence is formatted as “For more information, see **Topic link** in the **Name of the guide.**”
4. To create the topic link, format it as follows:
    ```
    `This is the topic title <https://link.to.the/topic/page>`__
    ```
    1. The link begins with a single back tick, followed by the title text for the link.
    2. The title text must be followed by a single space, then the ``<`` that introduces the link.
    3. The link URL must be between ``<>`` characters with no extra spaces.
    4. The ``<>`` must be followed by a closing back tick `` ` ``(no spaces) and two underscores.
5. The guide name should have a single asterisk on either side of it followed by a period.
    ```
    in the *Name of the guide*.
    ```