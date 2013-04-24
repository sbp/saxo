# Getting started

## Requirements

* **Python 3.3** or later
* **Sqlite 3** libraries installed
* Thread-safe compilation of Sqlite 3 in Python 3.3

## Installation

### Using pip and pypy

This the recommended method of installation.

```sh
pip3 install saxo
```

You now have a `saxo` command you can run.

### Development version from Github

```sh
git clone https://github.com/sbp/saxo.git
cd saxo
```

You now have a `./saxo` command you can run.

Then, optionally:

* **Either**: `python3 setup.py install`
* **Or**: `pip3 install .`

Which will additionally give a `saxo` command.

## Usage

### Create an bot instance

You need to create a bot first:

```sh
saxo create
```

This creates a `~/.saxo` **base directory** and populates it with some files, including a config file at `~/.saxo/config` which you should edit using the values described in [Saxo config](config.md).

If you want to create a base directory in a different location, you can pass a directory:

```sh
saxo create ~/my-saxo
```

This will create `~/my-saxo` and populate it with files, including `~/my-saxo/config`. You can use `.` as the base directory in order to use the current directory.

### Run the bot instance

To run the bot that you created:

```sh
saxo start
```

This uses `~/.saxo` as the base directory. You can also pass it a directory argument if you created your own, non-default base directory:

```sh
saxo start ~/my-saxo
```

These commands fork saxo into the background, running as a daemon. There will be no output except to say what PID saxo is using; the PID will also be saved in a `pid` file in the base directory.

If you want to log output, both **stdout** and **stderr**, to a file, you can use the `-o` option in conjunction with the `start` action:

```sh
saxo -o ~/saxo.log start
```

Will log output to `~/saxo.log`. You can use relative paths too.

If you don't want to fork saxo into the background, you can use the `-f` option:

```sh
saxo -f start
```

This will start the default base saxo and log output to the term. You can also use the `-f` option in conjunction with the `-o` option if you would like to run the bot in the foreground but not log.

### Stop the bot instance

To stop saxo:

```sh
saxo stop
```

Again, you can pass a directory if you are not using the base directory:

```sh
saxo stop ~/my-saxo
```

### Summary

* `saxo -v` — Print the saxo version
* `saxo create [ directory ]` — Create a saxo base directory
* `saxo [ -f ] [ -o filename ] start [ directory ]` — Start a saxo bot
* `saxo stop [ directory ]` — Stop a saxo bot
* `saxo active [ directory ]` — Discover whether saxo is running

Try `saxo -h` for more detailed usage.

## Extending saxo

To extend saxo, read about [writing your own saxo commands](write-commands.md).
