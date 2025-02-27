#!/bin/bash

echo '
                      888                 d8b                   d8b                  
                      888                 Y8P                   Y8P                  
                      888                                                            
 .d8888b .d88b.   .d88888 888  888       8888 888  888 88888b.  888  .d88b.  888d888 
d88P"   d88""88b d88" 888 `Y8bd8P`       "888 888  888 888 "88b 888 d88""88b 888P"   
888     888  888 888  888   X88K  888888  888 888  888 888  888 888 888  888 888     
Y88b.   Y88..88P Y88b 888 .d8""8b.        888 Y88b 888 888  888 888 Y88..88P 888     
 "Y8888P "Y88P"   "Y88888 888  888        888  "Y88888 888  888 888  "Y88P"  888     
                                          888                                        
                                         d88P                                        
                                       888P'

if [ "$CODX_APPS" != "" ]; then
  for app in ${CODX_APPS//,/ }
  do
    echo "Installing codx app: $app"
    codx $app
  done
fi

# Run supervisor
echo "Running supervisor"
/usr/bin/supervisord -c ${CODX_JUNIOR_PATH}/supervisor.conf