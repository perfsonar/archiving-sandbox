FROM centos:centos8

#install requirements
RUN \
    dnf update -y && \
    dnf install -y epel-release && \
    dnf install -y python3 python3-flask python3-elasticsearch python3-isodate python3-dateutil python3-urllib3

#shared volume
VOLUME /app

#Run our app
WORKDIR /app
ENTRYPOINT ["python3"]
CMD ["app.py"]