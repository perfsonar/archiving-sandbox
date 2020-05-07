FROM centos:centos8

#install requirements
RUN \
    dnf update -y && \
    dnf install -y epel-release && \
    dnf install -y python3 python3-requests

#shared volumes
VOLUME /app

#Run the script and exit
WORKDIR /app
ENTRYPOINT ["python3"]
CMD ["pselastic", "-c", "/app/resources", "-u", "http://elasticsearch:9200", "--max-retries", "120", "install", "ilm"]