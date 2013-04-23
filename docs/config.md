# Saxo config

To set options for saxo such as which server to connect to and which nickname to use, add setting to the `config` file. This file lives in the base directory created when you ran `saxo create`. The default location is `~/.saxo/config`.

The `config` file uses INI format. Here's an example:

```ini
[server]
    host = irc.freenode.net
    port = 6667

[client]
    nick = saxo67301
    channels = ##saxo #test
    prefix = .
```

## Sections

The following sections are valid:

* `[server]` — Options about the server that saxo connects to
* `[client]` — Options about saxo itself
* `[plugins]` — Options about saxo plugins

## [server]

**host**

Hostname of the server to connect to. Can be a domain or an IPv4 address.

Example: `irc.freenode.net`

**port**

Number of the port to connect to.

Example: `6667`.

**password**

Password of the server.

Example: `m18+9289\721j%aikhi@af1986691$oha&hof`

**ssl**

Whether or not to use ssl. Leave unset to not use ssl.

**WARNING**: *This option does not validate the certificate.*

Example: `True`

## [client]

**channels**

A space separated list of channels to join.

Example: `##saxo #test`

**nick**

The nickname of the bot.

Example: `saxobot`

**owner**

Full IRC address of the owner of the bot. This enables the user with that address to use admin functions.

Example: `nick!~user@subdomain.example.org`

**prefix**

The prefix to use for commands. Using `.` for example would allow commands such as `.version`.

Example: `.`

## [plugins]

User defined `config` options should go here. There is one pre-defined one:

**nickserv**

Password to use for nickserv, compatible with Freenode only by default.

Example: `51&5NW8_N95+W679=d567w3@56dw9!FYU*T`
