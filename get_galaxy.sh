#!/bin/sh

rm galaxy_stations.*
wget https://downloads.spansh.co.uk/galaxy_stations.json.gz
gzip -d galaxy_stations.json.gz
