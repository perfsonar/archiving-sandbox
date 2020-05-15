ARG GRAFANA_VERSION="7.0.0-beta3"
ARG WIZZY_VERSION="0.7.0"

FROM grafana/grafana:${GRAFANA_VERSION}-ubuntu

#Install wizzy
USER root
RUN curl -sL https://deb.nodesource.com/setup_14.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g wizzy@${WIZZY_VERSION}
COPY scripts/docker-sync.sh /usr/local/bin/
USER grafana

# Install external plugins
ENV GF_INSTALL_PLUGINS=grafana-worldmap-panel
