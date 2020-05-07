FROM centos:centos8

#install requirements
RUN \
    dnf update -y && \
    dnf install -y epel-release && \
    dnf install -y python3 python3-requests

#shared volumes
VOLUME /app

#Run the script to install ILM policies then run in periodic mode to 
#install rollups as needed. Thiis is because rollups need an index to exist 
#before they can do a rollup
WORKDIR /app
CMD \
    python3 pselastic -u http://elasticsearch:9200 --max-retries 120 install ilm && \
    python3 pselastic -u http://elasticsearch:9200 --periodic 60 install rollups