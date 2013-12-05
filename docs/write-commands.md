# Write saxo commands

## Summary

Add new commands by creating scripts in the `commands` directory. This script, for example:

```sh
#!/bin/sh
echo "Hello $SAXO_NICK"
```

Saved into `commands/hello` gives this output when used:

```
<user> .hello
<saxo> Hello user
```

## What are commands?

When users interact with saxo, they normally do so with commands. Commands are invoked using a prefix character, the name of the command, and then some optional arguments. Some examples of commands:

```
.in 3m the egg is cooked
.to sbp this message system is great
```

These commands are called `in` and `to`, and their arguments are `3m the egg is cooked` and `sbp this message system is great`. The code behind the commands will make the bot give a reminder in three minutes and send a message to the user `sbp` respectively.

### Where commands live

Commands in saxo can be written in any language. They live in the `commands` directory in the saxo base directory. The base directory is the one created by the user by running `saxo create`, and is `~/.saxo` by default, so usually commands live in `~/.saxo/commands`.

If the user created their own directory, then it would be in a different location. For example, if they ran `saxo create ~/my-saxo` then the commands will live in `~/my-saxo/commands`.

By default, saxo will populate the `commands` directory with all of the pre-existing commands that ship with it. These commands are *symlinked* to the saxo package directory, which is in a system dependent location. Whenever saxo runs, it automatically updates any symlinks so that you always have symlinks to the latest commands in your `commands` directory.

## Add to the commands directory

To add your own command, you will add a new script to the `commands` directory. You don't have to symlink to a script, you can just put a file straight into the directory. You can even remove an existing symlink and put your own file in there in place of the old command. Then you will have replaced the old command with your own version.

Here's a simple "Hello, world!" command:

```python
#!/usr/bin/env python3
print("Hello, world!")
```

If you save that into `commands/hello`, make sure that it is executable (usually by running `chmod 755 commands/hello` or something similar), and then either restart saxo or run the `.reload` command, then you will have a new command in saxo called `.hello`. It should work like this:

```
<user> .hello
<saxo> Hello, world!
```

Since commands can be written in any language, we could also write in, say, bash:

```bash
#!/bin/bash
echo 'Hello, world!'
```

Which we would put in the same place, `commands/hello`. We could even write it in C if we wanted:

```c
#include <stdlib.h>
#include <stdio.h>

int main(void) {
    printf("Hello, world!\n");
    return EXIT_SUCCESS;
}
```

Which we would save as `hello.c`, compile, and then move into place:

```
$ gcc -O3 -o hello hello.c
$ chmod 755 hello
$ mv -p hello ~/.saxo/commands/hello
```

## Getting into arguments

Saxo takes the first line (only) of the output from a command script, and uses that as the response from the command. You can already do a great deal with this. For example, you could write a script that displays the current uptime on your system:

```sh
#!/bin/sh
uptime
```

Or even get something from the web and display information about that. But eventually you'll probably want to do more than just print output. The most common thing you'll want to do is receive input from the user, obtaining the *argument* that was sent along with the command. You can do this in either of two ways:

* Read the first positional argument given to the program, **argv[1]**
* Read a line from **stdin**

The following commands all do the same thing, simply printing out the argument passed from the user:

```bash
#!/bin/bash
echo "$1"
```

```bash
#!/bin/bash
head -n 1
```

```bash
#!/bin/bash
read LINE
echo "$LINE"
```

Try saving these as `commands/echo1`, `commands/echo2`, and `commands/echo3` to test them.

```
<user> .echo1 this is an example
<saxo> this is an example
<user> .echo2 does this one work too?
<saxo> does this one work too?
<user> .echo3 what are you, some kind of myner bird?
<saxo> what are you, some kind of myner bird?
```

## The python privilege

If you use python for your commands, you are privileged. Saxo provides an interface called the `@saxo.pipe` decorator that enables you to write commands more easily. Here's what you get when you use `@saxo.pipe`:

* concise code
* clean exiting
* input surrogate decoding
* output encoding
* a custom error wrapper

So for example, let's say we make the following command:

```python
#!/usr/bin/env python3
print(1/0)
```

We save that as `commands/infinity-and-beyond` and test it:

```
<user> .infinity-and-beyond
<saxo> Sorry, .infinity-and-beyond did not respond
```

Oh dear, the command broke. Why did it break? Let's look at the console output from saxo:

```
Traceback (most recent call last):
  File "/Users/user/.saxo/commands/infinity-and-beyond", line 2, in <module>
    print(1/0)
ZeroDivisionError: division by zero
```

Okay, but wouldn't it be nice to learn about this from saxo in irc, without having to check the console? Let's try again using the `@saxo.pipe` decorator:

```python
#!/usr/bin/env python3

import saxo

@saxo.pipe
def infinity_and_beyond(arg):
    return str(1/0)
```

It's slightly more code, but now we get the error in irc:

```
<user> .infinity-and-beyond
<saxo> ZeroDivisionError: division by zero (infinity-and-beyond:7)
```

You don't have to use the `@saxo.pipe` decorator, but if you use python3 it's there if you want it.

## Use the environment

You can access more information than just the argument passed by the user. What if, for example, you wanted to know the nickname of the user issuing the command? For example, let's say you want to do this:

```
<user> .whoami
<saxo> Your nickname is user
```

Information like this is available from the shell environment. The way that you access this is dependent on the language that you use. Here is an example of the `commands/whoami` function in both bash and python:

```bash
#!/bin/bash
echo "Your nickname is $SAXO_NICK"
```

```python
#!/usr/bin/env python3
import os
print("Your nickname is", os.environ["SAXO_NICK"])
```

Though bash makes it slightly easier than python, it's reasonably straightforward in both languages.

Here are some environment variables you can use:

* `SAXO_BASE` — the path of the base directory that saxo is using
* `SAXO_COMMANDS` — the path of the commands directory. equivalent to `$SAXO_BASE/commands`
* `SAXO_NICK` — the nickname of the user issuing the command
* `SAXO_IDENTIFIED` — whether the user is identified with the network
* `SAXO_SENDER` — the channel where the command was issued
* `SAXO_BOT` — the nickname that saxo is using itself
* `SAXO_URL` — the most recently mentioned URL in the channel where the command was issued

The `SAXO_IDENTIFIED` environment variable is only present when the host IRC network supports this feature.

These environment variables are only available when a command is run by the bot. If you are writing a command that also functions as a CLI script, you must check for the presence of an environment variable before using it.

Using `SAXO_COMMANDS` makes it possible to call commands in other commands. Because they're just shell scripts and use a simple **argv[1]** or **stdin** interface, you can easily make commands that work together nicely.

```bash
#!/bin/bash
echo "https://duckduckgo.com/?q=$($SAXO_COMMANDS/quote-url "$1")"
```

— `commands/duck-url`

```python
#!/usr/bin/env python3
import saxo
import urllib.parse

@saxo.pipe
def quote_url(url):
    return urllib.parse.quote(url)
```

— `commands/quote-url`

```
<user> .duck-url café wha?
<saxo> https://duckduckgo.com/?q=caf%C3%A9%20wha%3F
```

Because commands are just simple scripts, you can also run them from the command line:

```
$ commands/duck-url 'café wha?'
https://duckduckgo.com/?q=caf%C3%A9%20wha%3F
```

You could even add the commands to your `$PATH`:

```
$ export PATH=~/.saxo/commands:$PATH
$ duck-url 'café wha?'
https://duckduckgo.com/?q=caf%C3%A9%20wha%3F
```

## The communication nation

Sometimes you may want to do something a bit more advanced, such as set a channel topic. You can do this by communicating with saxo using a socket as IPC. If you use python3, you can import the saxo module and do this with ease:

```python
#!/usr/bin/env python3

import os
import saxo

@saxo.pipe
def topic(arg):
    channel = os.environ["SAXO_SENDER"]
    if channel.startswith("#"):
        saxo.client("send", "TOPIC",  channel, arg)
    else:
        return "Sorry, you're not in a channel"
```

TODO: Sending without pickling.

## Hints and tips

* Once a module is loaded, you don't have to reload it once you change it
* Python startup speed is negligibly slower than C
* Case-sensitivity of commands depends on your filesystem
* Returning nothing from a command will mean there is no output, as long as the exit code is `0`.
* You can't presently return more than one line from a command; use `saxo.client` to do that.
