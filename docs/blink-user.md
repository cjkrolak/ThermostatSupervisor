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
`BLINK_2FA` is loaded at runtime and can use a fallback value if missing, but
Blink authentication will fail unless a valid current code is available.

## Where to Store Blink Login Information

### Preferred: `supervisor-env.txt` in project root

Create `supervisor-env.txt` in the repository root with key/value pairs:

```text
BLINK_USERNAME=your_blink_username
BLINK_PASSWORD=your_blink_password
BLINK_2FA=123456
```

- Location: repository root (same directory where you run `python -m src.*`)
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

ThermostatSupervisor uses Blink authentication with `no_prompt=True`, so you
must provide a current 2FA code before startup.

1. Open your Blink-linked authenticator app (or the Blink account 2FA source
   configured for your account).
2. Generate a fresh 2FA code.
3. Update `BLINK_2FA` in `supervisor-env.txt` (or your exported env var).
4. Start or restart the Blink module or supervisor process.

```bash
python -m src.blink blink 0
```

Important:
- 2FA codes are short-lived and can expire in under a minute.
- If authentication fails with 2FA errors, generate a new code and retry.

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
