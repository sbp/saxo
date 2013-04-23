# Changes

## 0.1.005 to 0.2.001

### Summary

* `saxo.communicate` is now `saxo.client`
* `irc.queue` is now `irc.client`
* `irc.client` is now split into items in `irc.config`
* `irc.server` is now `irc.config["server"]`

### Specifics

```python
saxo.communicate("instruction", ("a", 2, []))
```

Becomes:

```python
saxo.client("instruction", "a", 2, [])
```

And:

```python
irc.queue(("instruction", "a", 2, []))
```

Becomes:

```python
irc.client("instruction", "a", 2, [])
```

For obvious consistency.

* `irc.client["channels"]` is now `irc.config["channels"]`
* `irc.client["nick"]` is now `irc.config["nick"]`
* `irc.client["owner"]` is now `irc.config["owner"]`
* `irc.client["prefix"]` is now `irc.config["prefix"]`

No other attributes in `[client]` in the `config` file are currently copied.

There is also a new `[plugins]` section.
