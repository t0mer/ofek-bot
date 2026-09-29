# Ofek-bot

Ofek-bot is a Python bot that logs in to the **Ofek** learning website by CET, used in Israeli
schools ([myofek.cet.ac.il](https://myofek.cet.ac.il/he)), on behalf of each of your kids.
It signs in through the Ministry of Education's SSO (edu.gov.il), reads their task counters, and sends you a notification through
[Apprise](https://github.com/caronc/apprise) when a kid has tasks to complete or fix. It runs
on a daily schedule inside a Docker container with a headless Chrome browser driven by
Selenium.

> [!IMPORTANT]
> **Unofficial project.** Ofek-bot is not affiliated with, endorsed by, or supported by Ofek,
> CET, the Israeli Ministry of Education, or any school. It automates a normal browser login
> with credentials you provide. You are responsible for making sure your use complies with the
> website's terms of use and your school's policies.

## Table of contents

- [Features](#features)
- [How it works](#how-it-works)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Notifications](#notifications)
- [Logging](#logging)
- [Troubleshooting](#troubleshooting)
- [Security and privacy](#security-and-privacy)
- [Known issues and limitations](#known-issues-and-limitations)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Features

- Monitors the Ofek task status of any number of kids, each with their own login.
- Logs in through the edu.gov.il SSO using the username/password option.
- Reads four counters from the Ofek dashboard: tasks to do, tasks to fix, checked tasks, and
  tasks waiting for review.
- Notifies only when there is something to do (the "to do" or "to fix" counter is above zero).
- Runs on one or more daily schedules (default: 16:00).
- Supports many notification channels (Telegram, Discord, Slack, email, Pushover, Home
  Assistant, and more), thanks to [Apprise](https://github.com/caronc/apprise).

### Components and frameworks

- [Loguru](https://pypi.org/project/loguru/) for logging.
- [Schedule](https://pypi.org/project/schedule/) for the run schedule.
- [Apprise](https://github.com/caronc/apprise) for notifications.
- [Selenium](https://selenium-python.readthedocs.io/) and
  [webdriver-manager](https://pypi.org/project/webdriver-manager/) for browser automation.
- [PyYAML](https://pypi.org/project/PyYAML/) for the configuration file.

## How it works

```mermaid
flowchart TD
    A[Start: load config/config.yaml<br/>and NOTIFIERS / SCHEDULES] --> B{Scheduled time?}
    B -- no --> B
    B -- yes --> C[For each kid in config]
    C --> V{name, username and<br/>password all set?}
    V -- no --> X[Log warning and<br/>stop this run]
    V -- yes --> D[Start headless Chrome]
    D --> E[Open myofek.cet.ac.il/he<br/>and click Login]
    E --> F[Choose edu.gov.il SSO,<br/>switch to username/password login]
    F --> G[Enter the kid's username and password]
    G --> H[Read the four task counters<br/>from the dashboard]
    H --> I{To do > 0 or<br/>to fix > 0?}
    I -- yes --> J[Send Apprise notification]
    I -- no --> K[Log: no tasks]
    J --> L[Close browser]
    K --> L
    L --> C
```

The diagram shows the normal path. If a scrape fails, the error is logged and the previous
counter values are kept. If no counter has been read since the bot started, the counter check
raises an error that ends the run for all remaining kids (see
[Known issues and limitations](#known-issues-and-limitations)).

1. On startup the bot loads the kids list from `config/config.yaml` (relative to the working
   directory, `/app` in the container). If the file does not exist, it copies the empty
   template `config.yaml` there. The file is read **once**, so restart the bot after you
   change it.
2. It registers every Apprise URL from `NOTIFIERS` and one daily job for every time in
   `SCHEDULES`.
3. At each scheduled time, for every kid, it starts a fresh headless Chrome session
   (incognito, `--no-sandbox`, `--disable-dev-shm-usage`), logs in to Ofek through the
   edu.gov.il SSO, and reads the text of the four counters on the dashboard.
4. It takes the first number in the "to do" and "to fix" counters. If either is greater than
   zero, it sends a notification; otherwise it logs that there are no tasks.

There is no stored state or de-duplication: as long as a kid has open tasks, you get a
notification at **every** scheduled run.

## Requirements

- Docker (recommended), **or** Python 3 with Google Chrome installed locally.
- Outbound internet access to `myofek.cet.ac.il`, the edu.gov.il login pages, and your
  notification services. `webdriver-manager` also downloads a matching ChromeDriver at run
  time, so it needs internet access too.
- An Ofek (edu.gov.il) **username and password** for each kid. The bot uses the
  username/password login, not the SMS login.
- At least one [Apprise URL](https://github.com/caronc/apprise/wiki) for notifications.

## Installation

### Docker Compose (recommended)

```yaml
services:
  ofek:
    image: techblog/ofek-bot:latest
    container_name: ofek
    restart: always
    environment:
      - SCHEDULES=16:00
      - NOTIFIERS=tgram://<bot_token>/<chat_id>
    volumes:
      - ./ofek-bot/config:/app/config
```

1. Create the config folder and the `config.yaml` file described in
   [Configuration](#configuration):
   ```bash
   mkdir -p ofek-bot/config
   nano ofek-bot/config/config.yaml
   ```
2. Start the container:
   ```bash
   docker compose up -d
   docker compose logs -f ofek
   ```

### Docker

```bash
docker run -d --name ofek --restart always \
  -e SCHEDULES="07:30,16:00" \
  -e NOTIFIERS="tgram://<bot_token>/<chat_id>" \
  -v "$(pwd)/ofek-bot/config:/app/config" \
  techblog/ofek-bot:latest
```

### Published images

Images are published to Docker Hub as
[`techblog/ofek-bot`](https://hub.docker.com/r/techblog/ofek-bot) for `linux/amd64` only.
The tags are `latest` and the version from the [`VERSION`](VERSION) file. There are no GitHub
Releases.

> [!NOTE]
> At the time of writing, the newest tag on Docker Hub is `3.2.1` (September 2024), which is
> also `latest`. The current `VERSION` file says `3.3.1`, and the Dockerfile on `main` (based
> on `selenium/standalone-chrome`) has not been published yet. Until a new image is built,
> `latest` is built from an older Dockerfile. <!-- TODO: verify after the next image build -->

### From source

```bash
git clone https://github.com/t0mer/ofek-bot.git
cd ofek-bot
pip3 install -r requirements.txt

cd app                           # the bot reads config/config.yaml relative to this folder
mkdir -p config
cp config.yaml config/config.yaml
nano config/config.yaml          # add your kids

export NOTIFIERS="tgram://<bot_token>/<chat_id>"   # must be set, even to ""
export SCHEDULES="16:00"
python3 app.py
```

Google Chrome must be installed; `webdriver-manager` downloads the matching ChromeDriver.

## Configuration

Configuration comes from two environment variables and one YAML file. There are no command
line flags.

### Environment variables

| Variable | Required | Default | Description |
| -------- | -------- | ------- | ----------- |
| `NOTIFIERS` | Yes, to get notifications | `""` in the Docker image; unset outside Docker | One or more [Apprise URLs](#notifications), separated by **spaces**. If empty, the bot still checks Ofek but sends nothing. Outside Docker it must be set (even to an empty string), or the bot exits on startup. |
| `SCHEDULES` | No | `16:00` | Daily run times in 24-hour `HH:MM` format, separated by commas **without spaces**, for example `07:30,16:00`. Times use the container's local time zone. |
| `TZ` | No | `UTC` (from the `selenium/standalone-chrome` base image) | Time zone for `SCHEDULES`, for example `Asia/Jerusalem`. The `selenium/standalone-chrome` base image supports it; the bot itself does not read it. |

### `config/config.yaml`

The kids list is stored in `/app/config/config.yaml` inside the container. Mount a host folder
to `/app/config` so the file survives container updates.

| Key | Required | Description |
| --- | -------- | ----------- |
| `kids` | Yes | List of kids to check. |
| `kids[].name` | Yes | Display name. Used in the notification title and the logs only. |
| `kids[].username` | Yes | The kid's edu.gov.il username (usually the ID number). Numbers are converted to strings. |
| `kids[].password` | Yes | The kid's edu.gov.il password. |

Example:

```yaml
kids:
  - name: Kid1
    username: "000000000"
    password: "<password>"

  - name: Kid2
    username: "000000000"
    password: "<password>"
```

Quote usernames with leading zeros (`"012345678"`), or YAML may misread them as numbers
(including octal) and change the value.

All three keys are required for every entry. When the bot reaches an entry with an empty
`name`, `username`, or `password`, it logs `Kids list is empty or not configured` and **stops
processing the rest of the list** for that run. Remove unused entries instead of leaving them
blank.

## Notifications

Set `NOTIFIERS` to one or more Apprise URLs separated by spaces:

```bash
NOTIFIERS="tgram://<bot_token>/<chat_id> pover://<user_key>@<app_token>"
```

A few common examples (see the [Apprise wiki](https://github.com/caronc/apprise/wiki) for the
full, current list of services and URL formats):

| Service | Example URL |
| ------- | ----------- |
| [Telegram](https://github.com/caronc/apprise/wiki/Notify_telegram) | `tgram://bottoken/ChatID` |
| [Discord](https://github.com/caronc/apprise/wiki/Notify_discord) | `discord://webhook_id/webhook_token` |
| [Slack](https://github.com/caronc/apprise/wiki/Notify_slack) | `slack://TokenA/TokenB/TokenC/Channel` |
| [Pushover](https://github.com/caronc/apprise/wiki/Notify_pushover) | `pover://user@token` |
| [Gotify](https://github.com/caronc/apprise/wiki/Notify_gotify) | `gotifys://hostname/token` |
| [ntfy](https://github.com/caronc/apprise/wiki/Notify_ntfy) | `ntfys://hostname/topic` |
| [Home Assistant](https://github.com/caronc/apprise/wiki/Notify_homeassistant) | `hassio://hostname/accesstoken` |
| [Microsoft Teams](https://github.com/caronc/apprise/wiki/Notify_msteams) | `msteams://TokenA/TokenB/TokenC/` |
| [MQTT](https://github.com/caronc/apprise/wiki/Notify_mqtt) | `mqtt://user:pass@hostname/topic` |
| [Email](https://github.com/caronc/apprise/wiki/Notify_email) | `mailtos://user:password@gmail.com` |
| [Apprise API](https://github.com/caronc/apprise/wiki/Notify_apprise_api) | `apprises://hostname/Token` |

### Message format

A notification is sent per kid, only when the "to do" or "to fix" counter is above zero.

- **Title:** `מצב משימות אופק של <name>` ("Ofek task status of &lt;name&gt;").
- **Body:** the text of the four dashboard counters exactly as Ofek shows them (in Hebrew),
  one per line, in this order: to do, to fix, checked, waiting.

## Logging

The bot logs to standard error with Loguru's default format at `DEBUG` level. The level is
not configurable. View the logs with `docker logs -f ofek`.

Useful messages: `Loading kids list`, `Getting tasks for: <name>`, `Scrapping...`,
`No tasks tbd for <name>`, `Setting default schedule to 16:00` (when `SCHEDULES` is empty),
and `Setting schedule to everyday at <time>`.

## Troubleshooting

- **Nothing happens after startup.** The bot waits for the next scheduled time. Check the
  `Setting default schedule to 16:00` or `Setting schedule to everyday at <time>` lines in
  the log and the container's time zone (see `TZ`).
- **The container exits at startup with a schedule error.** Each `SCHEDULES` entry must be a
  valid `HH:MM` time, separated by commas without spaces (`07:30,16:00`, not `07:30, 16:00`).
- **No notifications arrive.** Check that `NOTIFIERS` is set, that multiple URLs are separated
  by spaces (not commas), and that the log shows an `Adding: ...` line for each URL. Test each
  URL with the `apprise` CLI.
- **`Kids list is empty or not configured`.** An entry in `config.yaml` has an empty `name`,
  `username`, or `password`. The bot stops at the first such entry.
- **`config.yaml` is not created in the mounted folder.** The container runs as the
  non-root `seluser`. Create `config/config.yaml` yourself, or make the host folder writable
  by that user.
- **Timeout or "no such element" errors while logging in or scraping.** The bot uses fixed
  XPaths and a 5-second wait for each step. If Ofek or the edu.gov.il login page changes its
  layout, these break and the code needs an update. Also check that the credentials work with
  the username/password login in a normal browser.
- **ChromeDriver download errors.** `webdriver-manager` checks for and, when not cached, downloads
  ChromeDriver on each run (the cache is lost when the container is recreated), so it needs
  internet access.

## Security and privacy

- `config.yaml` holds your kids' **Ministry of Education credentials in plain text**. Keep it
  out of version control, restrict its permissions (for example `chmod 600`), and store it
  only on a host you trust.
- Apprise URLs usually contain API tokens. Treat `NOTIFIERS` as a secret: don't commit your
  compose file with real values; use an `.env` file or your orchestrator's secret store.
- At the default `DEBUG` log level the bot logs every Apprise URL it registers
  (`Adding: <url>`) and the kids' names. Protect the container logs accordingly.
- Notifications include your kid's name and task counts. Choose a private notification
  channel.
- The container runs Chrome as the non-root `seluser` with `--no-sandbox`. Don't expose it
  more than needed; the bot does not listen on any port.

## Known issues and limitations

- **Repeated alerts:** there is no state or de-duplication, so you get a notification at every
  scheduled run for as long as tasks are open.
- **Fragile scraping:** the scraper relies on absolute XPaths, fixed element ids and a
  hard-coded SSO URL rewrite (`EduCombinedAuthSms` to `EduCombinedAuthUidPwd`), so any change
  to the Ofek website or the edu.gov.il login can break the bot.
- **An empty entry stops the run:** an incomplete kid entry ends the run for the entries that
  follow it.
- **Stale counters after a failed scrape:** the counter values are not reset between kids. If
  scraping fails for a kid, the previous kid's values are kept and reported under the current
  kid's name.
- **A scrape failure can end the run:** if no counter has been read since the bot started, an
  `IndexError` ends the run for all remaining kids and leaves Chrome running, because
  `browser.quit()` is skipped.
- **Configuration is read once** at startup; restart the container after editing
  `config.yaml`.
- Images are built for `linux/amd64` only.

## Development

Project layout:

```
app/
  app.py         # the bot: scheduler, Selenium crawler, Apprise notifications
  config.yaml    # empty kids template, copied to config/config.yaml on first run
Dockerfile       # based on selenium/standalone-chrome; runs as seluser
requirements.txt # Python dependencies
VERSION          # image version tag used by the Docker workflow
.github/workflows/docker-image.yml
```

Run locally as described in [From source](#from-source). To build the image yourself:

```bash
docker build -t ofek-bot:dev .
docker run --rm -e NOTIFIERS="" -e SCHEDULES="16:00" \
  -v "$(pwd)/config:/app/config" ofek-bot:dev
```

The Dockerfile uses `selenium/standalone-chrome` as a base only to get Chrome; the entrypoint
is replaced with `python3 /app/app.py`, so no Selenium Grid server runs in the container.

The `docker` GitHub Actions workflow is started manually (`workflow_dispatch`). It builds for
`linux/amd64` and pushes `techblog/ofek-bot:latest` and `techblog/ofek-bot:<VERSION>`. Bump
`VERSION` before running it.

There are no automated tests.

## Contributing

Issues and pull requests are welcome. Since the bot depends on the Ofek website's layout,
reports about login or scraping failures (with the relevant log lines, **without**
credentials or personal data) are especially helpful.

## License

This project is licensed under the [Apache License 2.0](LICENSE).
