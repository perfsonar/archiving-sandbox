# archiving-sandbox

**THIS REPOSITORY IS NOT FOR PRODUCTION USE**

This is a repository to test out new types of archiving. **It is for development purposes only and should not be used in production environments.**  It currently contains a docker-compose file to bring up a set of preconfigured services that allow you to do the following:

 - Run a `pscheduler task` between two perfSONAR testpoint containers
 - Send the results to RabbitMQ
 - Read the RabbitMQ queue with Logstash and apply a set of filters
 - Write the result to ElasticSearch
 
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
4. Bring up the docker containers
```
docker-compose up -d
```
5. Login to the *testpoint* container:
```
docker-compose exec testpoint bash
```
6. Run a pscheduler test. Below is a throughput test run between the testpoint and target containers. You can run exactly as shown. 
```
pscheduler task throughput --source testpoint --dest target
```
7. When the test completes, navigate you browser to Kinana at http://localhost:5601. You can click **Discover** and follow thr prompts to browse your data.
