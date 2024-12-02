#!/bin/bash
if [ "$CODX_APPS" != "" ]; then
  for app in ${CODX_APPS//,/ }
  do
    echo "Installing codx app: $app"
    codx $app
  done
fi

# Run supervisor
echo "Running supervisor"
/usr/bin/supervisord -c /etc/supervisord/codx-junior.conf