#!/bin/sh
set -e

apk add --no-cache netcat-openbsd >/dev/null

# Minimal HTTP responder on 127.0.0.1:4000
# Body is {"status":"ok"} which is 15 bytes (no spaces).
BODY='{"status":"ok"}'
LEN=${#BODY}

# Keep serving forever
while true; do
  { 
    printf "HTTP/1.1 200 OK\r\n"
    printf "Content-Type: application/json\r\n"
    printf "Content-Length: %s\r\n" "$LEN"
    printf "Connection: close\r\n"
    printf "\r\n"
    printf "%s" "$BODY"
  } | nc -l -p 4000 -s 127.0.0.1 -q 1
done
