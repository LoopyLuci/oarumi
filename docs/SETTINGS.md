# Environment settings

> **Audience:** users configuring Oarumi, and contributors changing the settings code.

Oarumi reads its configuration from `OARUMI_*` environment variables. You can set
them in your shell, or store them once with the Settings window or the CLI. This
page explains where stored values live, how secrets are protected, and what the
app does (and does not do) with them.

---

## 1. Quick start

**GUI.** Start the app and open the **Settings** tab (Ctrl+5, or Ctrl+, from
anywhere). The left-hand list groups every setting. Each setting has a control
for its type, the value Oarumi is using right now, its default, and when a change
takes effect.

1. Change one or more settings. They stay pending, marked as unsaved, until you
   press **Save changes**. Nothing is written while you type.
2. **Save changes** checks every pending value first. If any is invalid, nothing
   is saved and the problem is shown next to the field.
3. Settings that apply after a restart show a banner with **Restart Oarumi now**.
   Log level applies at once.
4. **Revert** throws away unsaved edits. Closing the window or restarting asks
   what to do with unsaved edits first.

Use the search box to filter settings by name or description. **Secrets** has
its own page: type a value to store it in the keychain, **Reveal** shows a saved
secret for ten seconds, and **Remove** deletes it. **Custom** adds any other
`OARUMI_*` name. **File → Open settings folder** opens where `settings.json`
lives.

To open the app straight on this tab, run:

```bash
python -m desktop.settings
```

**CLI.**

```bash
python -m desktop.settings list
python -m desktop.settings set OARUMI_LOG_LEVEL DEBUG
python -m desktop.settings set OARUMI_API_TOKEN          # hidden prompt
printf '%s' "$VALUE" | python -m desktop.settings set OARUMI_API_TOKEN
python -m desktop.settings unset OARUMI_API_TOKEN
```

Values are never taken from the command line, so they do not end up in shell
history or the process list.

---

## 2. Where things are stored

| Kind | Where | Notes |
|---|---|---|
| **Secrets** (names containing `TOKEN`, `SECRET`, `PASSWORD`, `PASSWD`, `CREDENTIAL` or `KEY`, or forced with `--secret`) | Your OS keychain: Windows Credential Manager, macOS Keychain, or Secret Service on Linux. Service name `oarumi`. | Values only. |
| **Everything else** | `settings.json` in the user config directory. | Windows: `%APPDATA%\oarumi\`. Other systems: `$XDG_CONFIG_HOME/oarumi/` or `~/.config/oarumi/`. Override with `OARUMI_CONFIG_DIR`. |

`settings.json` lists the names of your secrets, but never their values:

```json
{
  "version": 1,
  "values": { "OARUMI_LOG_LEVEL": "DEBUG" },
  "secrets": ["OARUMI_API_TOKEN"]
}
```

Nothing is written inside the repository. The `.env` file in the repo root is
ignored by git, and the app does not read it.

---

## 3. Security model

Oarumi aims to make a secret leak hard, not just unlikely:

1. **No plaintext secrets on disk.** If no usable keychain exists, the app
   refuses to store a secret and says why. It never falls back to a file.
2. **Names are validated.** Only `OARUMI_[A-Z0-9_]+` names are accepted, so an
   unrelated variable such as `PATH` cannot be stored by mistake.
3. **Secret-looking names are always secrets**, even if you do not tick the box.
   You cannot store `OARUMI_API_TOKEN` as a plain value.
4. **Errors never echo a value.** A rejected value produces a message such as
   `OARUMI_LOG_LEVEL: must be one of DEBUG, INFO, WARNING, ERROR`, with the input
   left out.
5. **Masking everywhere in the UI.** Saved secrets are never displayed. The
   new-value box is a password field, and nothing is copied to the clipboard.
   **Reveal** is an explicit click, lasts ten seconds, and is cleared when you
   leave the Settings tab, save, revert or close the window.
6. **Log redaction.** At startup the app installs a filter that replaces every
   known secret value with `[REDACTED]` in log messages, arguments and
   tracebacks. Values shorter than four characters are not redacted, because
   they would blank out ordinary text. The filter is a backstop: the code is
   written so that it never logs a value.
7. **Shell wins.** A variable already set in your shell overrides the stored
   value, so CI and one-off runs behave as expected.
8. **Atomic, owner-only writes.** `settings.json` is written to a temporary file
   and then renamed. On Linux and macOS it is `0600`.

### Limits

- Anything you start from Oarumi inherits its environment, so a stored value
  can reach a child process you launch. Only store what that process needs.
- Once a value is in the environment, any code running as you can read it.
  Keychains protect values at rest, not from a process running as your user.
- The keychain is only as strong as your OS login. Lock your session.
- Redaction only covers values the app knows about: stored secrets and
  secret-looking `OARUMI_*` variables already in the environment.

---

## 4. Variables

Run `python -m desktop.settings list` for the live list with each variable's
status. The registry is `desktop/settings/registry.py`.

| Variable | Default | Applies | Meaning |
|---|---|---|---|
| `OARUMI_HOME` | repo root | restart | Data root that holds the language DB and models. Must be an existing folder. |
| `OARUMI_STRICT_PARITY` | `0` | restart | `1` makes any parity divergence a test failure. |
| `OARUMI_DEV_MODELS` | `1` | restart | `1` uses development model stubs. |
| `OARUMI_LOG_LEVEL` | `INFO` | now | `DEBUG`, `INFO`, `WARNING` or `ERROR`. |
| `OARUMI_OFFLINE` | `0` | restart | `1` disables every network call. The status bar shows the mode Oarumi started in. |
| `OARUMI_PARITY_HOST` | `127.0.0.1` | next run | Bind address for the parity web GUI. |
| `OARUMI_PARITY_PORT` | `8090` | next run | Port for the parity web GUI (1–65535). |
| `OARUMI_DISABLE_AVATAR` | `0` | restart | `1` hides the avatar widget. |
| `OARUMI_CONFIG_DIR` | per OS | shell only | Where `settings.json` lives. Cannot be stored. |

"Now" means the change takes effect when you save. "Restart" means it takes
effect when Oarumi next starts. "Next run" means it takes effect when the tool
that reads it next starts, such as the parity web GUI.

Custom `OARUMI_*` names are accepted too. They are stored as text unless the
name looks secret.

---

## 5. For contributors

- `desktop/settings/registry.py` defines names, kinds, validation, the sidebar
  group, and when a change applies. Add a variable there, and add it to
  `.env.example` and the table above.
- `desktop/views/settings.py` is the Settings tab. It only edits pending values;
  `save()` validates everything before writing anything.
- `desktop/settings/manager.py` is the only code that reads or writes stored
  values. The GUI, CLI and startup all go through `EnvManager`.
- `desktop/settings/store.py` holds the keychain adapter and the atomic file.
  `KeyringSecretStore` refuses `fail` and `null` keyring backends.
- `desktop/settings/redact.py` installs the log filter. `app.py` calls
  `load_settings()` before anything else runs.
- Tests use an in-memory keyring (`desktop/tests/keyring_fake.py`), so they never
  touch the real keychain. Every test file for this feature is named
  `desktop/tests/test_settings_*.py`, and the tab is tested in
  `desktop/tests/test_settings_view.py`.

Do not log, print, or include in an exception message any value from
`EnvManager`. If you need to show a status, show the name and whether it is set.
