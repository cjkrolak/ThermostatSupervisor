# Nest OAuth Token Generation

ThermostatSupervisor uses the `python-google-nest` package to access Nest
thermostats via the Google Device Access (SDM) API. This requires OAuth tokens
that are stored locally in a token cache file.

This guide explains how to generate the initial token cache (first-time
authorization) and where/how to store it so the supervisor can run unattended.

## What Gets Stored Where

ThermostatSupervisor's Nest integration uses these local files by default:

- `token_cache.json`: OAuth token cache (access + refresh token metadata)
- `credentials.json` (optional): OAuth client credentials. This file must use
  the following schema (note the non-standard `dac_project_id` field required
  by ThermostatSupervisor in addition to the standard Google fields):

  ```json
  {
    "web": {
      "client_id": "<your-oauth-client-id>",
      "client_secret": "<your-oauth-client-secret>",
      "dac_project_id": "<your-device-access-project-id>"
    }
  }
  ```

  This is **not** the unmodified file downloaded from the Google Cloud Console —
  you must add the `dac_project_id` key manually.

By default these paths are relative to the working directory where you start
the process:

- `token_cache.json` location is `./token_cache.json` (from `src/nest_config.py`)
- `credentials.json` location is `./credentials.json` (from `src/nest_config.py`)

Both files contain secrets and must not be committed to git. This repository's
`.gitignore` ignores `*.json`, and `supervisor-env.txt` is also ignored.

## Prerequisites

- A Google Device Access project (Device Access Console) with SDM API access
- A Google Cloud OAuth client (Web application) with a valid redirect URI
- The following values available:
  - `GCLOUD_CLIENT_ID`
  - `GCLOUD_CLIENT_SECRET`
  - `DAC_PROJECT_ID`

You can provide these values either as environment variables or via an optional
`credentials.json` file.

## Option A: Interactive First-Run Authorization (Recommended)

This is the simplest way to generate a fresh `token_cache.json`.

1. Set the required Nest credential environment variables:

   ```bash
   export GCLOUD_CLIENT_ID="..."
   export GCLOUD_CLIENT_SECRET="..."
   export DAC_PROJECT_ID="..."
   ```

2. Run the Nest module from the repository root:

   ```bash
   cd /path/to/ThermostatSupervisor
   python -m src.nest nest 0
   ```

3. When prompted, open the printed authorization URL in a browser, complete
   the Google consent flow, then paste the full callback URL back into the
   terminal.

4. Verify that `token_cache.json` was created in the current directory:

   ```bash
   ls -l token_cache.json
   ```

After this, normal supervisor runs should not prompt again unless your refresh
token is revoked or the cache file is deleted.

## Option B: Seed the Token Cache from Environment Variables

If you already have valid OAuth tokens (for example from a previous install),
ThermostatSupervisor can create `token_cache.json` automatically on startup.

1. Provide the tokens via environment variables:

   ```bash
   export NEST_ACCESS_TOKEN="<access_token>"
   export NEST_REFRESH_TOKEN="<refresh_token>"
   export NEST_TOKEN_EXPIRES_IN="3600"
   ```

2. Start the Nest module or the supervisor. If `token_cache.json` does not
   exist yet, it is created from these values on the first run.

## Storing Tokens for Long-Running Use

### Local development (environment variables)

`src/nest.py` reads `GCLOUD_CLIENT_ID`, `GCLOUD_CLIENT_SECRET`, and
`DAC_PROJECT_ID` directly from the shell environment via `os.environ`.
Unlike some other modules in this project, it does **not** load values from
`supervisor-env.txt` automatically, so entries in that file have no effect
on Nest credential resolution.

You must export the variables in your shell before running the Nest module:

```bash
export GCLOUD_CLIENT_ID=...
export GCLOUD_CLIENT_SECRET=...
export DAC_PROJECT_ID=...
```

Alternatively, you can keep the values in `supervisor-env.txt` for reference
and source the file into your shell before running:

```bash
set -o allexport && source supervisor-env.txt && set +o allexport
python -m src.nest nest 0
```

If you prefer not to export credentials into the shell environment, use
`credentials.json` instead (see Option B above and
`nest_config.use_credentials_file` in `src/nest_config.py`).

Optional (only needed to auto-create `token_cache.json` as in Option B):

```bash
export NEST_ACCESS_TOKEN=<access_token>
export NEST_REFRESH_TOKEN=<refresh_token>
export NEST_TOKEN_EXPIRES_IN=3600
```

### Production deployments

- Store `token_cache.json` somewhere persistent and readable by the service.
- Restrict permissions (example for Linux):

  ```bash
  chmod 600 token_cache.json
  ```

- If you run from a different working directory (systemd, Docker, etc.),
  ensure the process working directory matches where `token_cache.json` lives,
  or adjust the path in `src/nest_config.py` to a location under your config
  directory.

## Troubleshooting

- If you are repeatedly prompted to authorize:
  - Confirm `token_cache.json` exists where you start the process.
  - Confirm the OAuth client redirect URI matches the callback URL you paste.
  - If the refresh token was revoked, delete `token_cache.json` and rerun
    Option A.
