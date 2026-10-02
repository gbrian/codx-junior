# @codx mentions

Talk to codx-junior from inside your files. Write a comment that starts with `@codx` in any project file and save it; the background worker picks it up when the project is being watched.

```js
// @codx: add input validation and return a 400 error when the email is missing
function createUser(req, res) {
  ...
}
```

codx-junior can:

* change the file as requested,
* explain a piece of code,
* suggest improvements.

While it works, the mention is marked with `codx-ok, please-wait...`. If something goes wrong it is marked with `codx-error`.

## Formats

| Format | Example |
| --- | --- |
| Single line | `@codx: refactor this function --knowledge` |
| Multi-line block | `<codx> ...instructions on several lines... </codx>` |
| Block with attributes | `<codx model="my-model"> ... </codx>` |

Flags are written as `--flag` or `--option=value`:

| Flag | Effect |
| --- | --- |
| `--knowledge` | Search the project's knowledge before changing the file. |
| `--model=<name>` | Use a specific model. |
| `--chat-id=<id>` | Continue an existing chat. |
| `--code` | Treat the request as a code change. |
| `--image` | Work with images. |
| `--vibe` | Use vibe coding mode. |

::: tip
Turn on **Watching** in the project settings so mentions are processed automatically. Turn on **Save mentions** to keep a chat for each mention.
:::
