#!/usr/bin/env bash
cd /app

if [ ! -e conf/wizzy.json ]; then
    cp conf/wizzy.json.default conf/wizzy.json
fi

wizzy set context grafana local #this should be the default, but just in case
wizzy export dashboards
wizzy export datasources

