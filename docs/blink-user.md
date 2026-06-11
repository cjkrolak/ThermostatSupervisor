# Blink User Setup

This guide covers Blink setup for ThermostatSupervisor, including credential
storage, zone configuration, 2FA handling, and environment variable precedence.

## Required and Optional Blink Keys

Blink support uses these environment variables:

- `BLINK_USERNAME` (required)
- `BLINK_PASSWORD` (required)
- `BLINK_2FA` (optional but required for successful authentication in most
  Blink accounts)

`BLINK_USERNAME` and `BLINK_PASSWORD` are validated before startup for Blink.
`BLINK_2FA` is loaded at runtime. If missing, the code uses a placeholder value
for logging/diagnostics only, and authentication will still fail until a valid
current code is provided.

## Where to Store Blink Login Information

### Preferred: `supervisor-env.txt` in current working directory

Create `supervisor-env.txt` in the directory where you run
ThermostatSupervisor with key/value pairs:

```text
BLINK_USERNAME=your_blink_username
BLINK_PASSWORD=your_blink_password
BLINK_2FA=123456
```

- Location: current working directory used to run `python -m src.*` (this is
  often the repository root)
- This file is ignored by git (`supervisor-env.txt` is in `.gitignore`)
- Use `supervisor-env.txt.example` as a template

### Alternative: process environment variables

You can export keys in your shell instead:

```bash
export BLINK_USERNAME="your_blink_username"
export BLINK_PASSWORD="your_blink_password"
export BLINK_2FA="123456"
```

## Login Source Precedence

For Blink keys, ThermostatSupervisor resolves values in this order:

1. `supervisor-env.txt`
2. system environment variables (`os.environ`)
3. default value defined in code (used only when the first two are missing)

If the same key exists in both `supervisor-env.txt` and your shell
environment, `supervisor-env.txt` wins.

## Blink 2FA Generation and Refresh

Blink requires a short-lived verification code for two-factor authentication.
When `blinkpy` initiates a login, Blink sends this code through the account's
configured 2FA delivery method.

### Step-by-step

1. **Trigger a login attempt.**  Run (or restart) the Blink module so that
   `blinkpy` contacts the Blink servers:

   ```bash
   python -m src.blink blink 0
   ```

2. **Retrieve the PIN from Blink.**  Check the email address (or SMS) linked to
   your Blink account.  Blink will send a message with a subject similar to
   *"Your Blink verification code"*.  The PIN is typically a 6-digit number
   and is valid for only a few minutes.

   You can also trigger a fresh PIN from the **Blink Home Monitor** mobile app
   (available for
   [iOS](https://apps.apple.com/us/app/blink-home-monitor/id1013961985) and
   [Android](https://play.google.com/store/apps/details?id=com.immedia.videocamera))
   by logging out of the app and logging back in.

3. **Update `BLINK_2FA`.**  Place the PIN value in `supervisor-env.txt` (or
   export it in your shell) before starting the supervisor:

   ```text
   BLINK_2FA=123456
   ```

4. **Start (or restart) the Blink module.**  The application reads `BLINK_2FA`
   at startup and passes it to `blinkpy` via `send_auth_key()`. The
   authentication object is created with `no_prompt=True`, so no interactive
   prompt is shown.

   ```bash
   python -m src.blink blink 0
   ```

### Important notes

- PINs expire quickly (often within 1–2 minutes).  Update `BLINK_2FA` and
  restart immediately after receiving the code.
- `blinkpy` cannot request a new PIN on your behalf; only Blink's servers
  initiate the delivery.
- If authentication fails with a 2FA error, generate a fresh PIN (repeat
  steps 1–4).

## Blink Zone Setup

Blink zones are configured in `src/blink_config.py` as a static metadata map:

- `metadata = {zone_number: {"zone_name": "<blink camera name>"}}`

To align ThermostatSupervisor with your Blink account:

1. Open `src/blink_config.py`.
2. Update each `zone_name` to exactly match the camera names in the Blink app.
3. Use the corresponding zone number in runtime arguments.

Example:

```bash
python -m src.blink blink 10
```

This selects zone `10`, which must map to the correct camera name in
`blink_config.metadata`.

## Troubleshooting

- `FATAL ERROR: required environment variable 'BLINK_USERNAME' is missing`
  or `BLINK_PASSWORD is missing`:
  - Add missing keys to `supervisor-env.txt` or export them in your shell.
- 2FA verification failure:
  - Refresh `BLINK_2FA` with a newly generated code and restart.
- Camera/zone mismatch:
  - Verify the `zone_name` in `src/blink_config.py` exactly matches the camera
    name shown in the Blink app.
