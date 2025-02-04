# MediacenterStatusUploader
## About
MediacenterStatusUploader is a python script that collects information about your mediacenter and uploads it to a google apps script (or other endpoint)

## What Can it check?
Currently it checks the status of Sonarr, Jackett, Radarr, Plex and Deluge, then uploads the collected status information to the REMOTE_STATUS_RECEIVER

## Running it standalone
Simply run `python3 ./fetcher.py` and update the default variables to suit your need. Remember to install the requirements from requirements.txt as well

## Running it with environment variables
```bash
export JACKETT_HOST=http://192.168.10.110:9117
export JACKETT_KEY=foo

export SONARR_BASE_URL=http://192.168.10.110:8989/
export SONARR_API_KEY=bar

export RADARR_BASE_URL=http://192.168.10.110:7878/
export RADARR_API_KEY=baz

export DELUGE_URL=http://192.168.10.110:8112/
export DELUGE_PASSWORD=spam

export PLEX_USERNAME=username@example.com
export PLEX_PASSWORD=somepassword

export REMOTE_STATUS_RECEIVER=https://....

python3 ./fetcher.py

```

## Running it periodically with docker
While docker compose is possible, I prefer running it on a standard unmodified container. This way the `Watchtower` container can update the underlaying container without needing to rely on building and publishing a custom image to dockerhub.

This will run the container every 25 minutes, and any ouput from the script will be stored in /var/log/cron.log
Environment variables will be loaded from the script directory, in the mediacenter.env files

Creating environment file:
```
cp mediacenter.env.example mediacenter.env
vim mediacenter.env #modify
```


Running it in background:
```bash
docker run -d --name python-cron \
  -v $(pwd):/usr/src/app \
  python:3-slim /bin/bash -c "
    apt-get update && apt-get install -y cron &&
    touch /var/log/cron.log &&
    pip install --no-cache-dir -r /usr/src/app/requirements.txt &&
    echo '*/25 * * * *  /usr/src/app/entrypoint.sh >> /var/log/cron.log 2>&1' > /etc/cron.d/mycron &&
    chmod 0644 /etc/cron.d/mycron &&
    crontab /etc/cron.d/mycron &&
    cron -f"

```

### Checking logs
```bash
docker exec -it python-cron cat /var/log/cron.log
```

## Excluding checks
set the environment variables CHECK_JACKETT, CHECK_SONARR, CHECK_DELUGE, CHECK_PLEX or CHECK_RADARR to "false", respectively
