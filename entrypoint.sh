#!/bin/sh

export $(grep -v '^#' /usr/src/app/mediacenter.env | xargs)

echo "Entrypoint listing env:"
printenv
echo "running main app"
/usr/local/bin/python3 /usr/src/app/fetcher.py
