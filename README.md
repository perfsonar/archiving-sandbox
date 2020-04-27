# archiving-sandbox

**THIS REPOSITORY IS NOT FOR PRODUCTION USE**

This is a repository to test out new types of archiving. **It is for development purposes only and should not be used in production environments.**  It currently contains a docker-compose file to bring up a set of pre-configured services that allow you to do the following:

 - Run a `pscheduler task` between two perfSONAR testpoint containers
 - Send the results to RabbitMQ
 - Read the RabbitMQ queue with Logstash and apply a set of filters
 - Write the result to ElasticSearch
 - Browse the ElasticSearch data with Kibana
 
## Quickstart

1. Install Docker on the machine where you plan to run the containers
2. Checkout this repository:
```
 git clone https://github.com/perfsonar/archiving-sandbox
```
3. Change your working driectory to the checked-out repository
```
cd archiving-sandbox

```
4. Copy `env.example` to `.env`. In general you don't need to change this file and just contains some advanced options.
```
cp env.example .env

```
5. Bring up the docker containers (this may take a minute, you can follow along with `docker-compose logs -f`):
```
docker-compose up -d
```
6. Login to the *testpoint* container:
```
docker-compose exec testpoint bash
```
7. Run a pscheduler test. Below is a throughput test run between the *testpoint* and *target* containers. You can run exactly as shown:
```
pscheduler task throughput --source testpoint --dest target
```
8. When the test completes, navigate you browser to Kibana at http://localhost:5601. You can click **Discover** and follow the prompts to browse your data.

## Containers

## Overview

The docker-compose file creates the following containers:

- **testpoint** - The standard perfsonar-testpoint container with a shared volume that mounts the `pscheduler_archives` directory in this repo into `/etc/pscheduler/default-archives`. By default, this directory contains an archiver definition that sends results to the *rabbit* container. Since this directory is where pscheduler defines its default archives, every `pscheduler task` command run on this container ships results to rabbit. 

- **target** - Another standard perfsonar-testpoint container with the main purpose of being the remote end of perfSONAR tests started on the *testpoint* container. It has no shared volumes or default archivers. 

- **rabbit** - A container running RabbitMQ. This is where pscheduler results from *testpoint* are sent. They wait in a queue until the *logstash* container reads the events. It has a web interface you can visit at http://localhost:15672 and sign in with guest/guest.

- **logstash** - Runs logstash using a pipeline defined in the `logstash_pipeline` directory of this repo. This directory is a shared volume, so changing files in that directory and restarting the container is how you experiment with different filters, etc. The pipeline gets input from the *rabbit* container and outputs to the *elasticsearch* container. The steps in between modify the event to get in the desired format before storage.

- **elasticsearch** - The ElasticSearch instance where the results from *logstash* are stored.

- **kibana** - A Kibana container you can use to browse ElasticSearch. You can access the Kibana interface at http://localhost:5601.

## Using the containers

You can bring up the container in the background with the following command:

```
docker-compose up -d
```
You can stop with the following:

```
docker-compose down -v
```

If you don't specify `-v` the next time you run the container all the data (not just the shared volumes) will be persisted. Sometimes this may be desirable but it can also cause problems for some of the containers (see *Tips and Troubleshooting* below).

You can view the logs for an individual container with `docker-composse logs -f [<container-name>]`. Examples:

```
docker-compose logs -f             # all logs
docker-compose logs -f logstash    # just logstash
```

You can execute a command in a conatiner with `docker-compose exec <container-name> <command>`. If the `<command>` is `bash` you will get a shell. Example:

```
docker-compose exec testpoint bash

```

## Tips and Troubleshooting

- Make sure you have enough memory allocated to containers in Docker. If you see elasticsearch crashing when you try to bring things up this is likely why. You can change this value in the "Preferences" of the Docker UI if you are using Mac or Windows. A value of 1GB seemed too low and 4GB seems to work, but you can probably get away with something in between if needed. 

- Sometimes for debugging purposes it is useful to run `docker-compose up`(i.e. drop `-d` mentioned in previous sections) so all the output from the containers is written to stdout. 

- The `.env` file contains settings if you want to point logstash at a different RabbitMQ instance and also control the logstash logging level. See the file for additional options.  Normally you don't need to touch this file, but if you start getting fancy it might help. These are essentially global environment variables so if you need to mess with $PATH or similar in the containers, you can do it here too. 

- The docker-compose file creates a network so all the containers can talk to each other using their container names. Thus when you login to testpoint if you run a test that talks to the `target` container you can simply add options like `--dest target`. Similarly you'll notice configs refer to `rabbit` when talking to the RabbitMQ container and similar.  

- In general you should use `-v` with `docker-compose down` to delete any "anonymous" volumes. These are volumes docker-compose creates that save the state of the container beyond the shared volumes we have defined. This is great if you want to keep the elastic data around, but it causes problems for `httpd` in the perfsonar containers in particular. If you don't use `-v` and one or both of the perfSONAR containers complain about not being able to find pscheduler, simply run the command `httpd` at the command-line (no `systemctl` in docker-land, so literally just type `httpd` at the command-line). 

- If you run a pscheduler test and it doesn't arrive in RabbitMQ check `/var/log/pscheduler.log` for a message like `archiver WARNING  Ignoring /etc/pscheduler/default-archives/rabbit.json: No archiver "rabbitmq" is avaiable.`. If this happens run your command with like `pscheduler task --archive /etc/pscheduler/default-archives/rabbit.json ...`. Need to investigate closer why this is happening. 

- If you need to run ruby in the logstash container to test a filter, run the following:
```
docker-compose exec logstash bash
export PATH="$PATH:/usr/share/logstash/vendor/jruby/bin"
ruby /path/to/script     #RUN A SCRIPT
irb                      #INTERACTIVE RUBY
```




