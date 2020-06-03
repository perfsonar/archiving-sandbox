#!/bin/bash

SCRIPT_DIR=$(dirname $0)
APP_DIR="$SCRIPT_DIR/../.."
SETUP_DIR="${APP_DIR}/pselastic_setup"
PASSWORD_DIR=/etc/perfsonar/elastic
PASSWORD_FILE=${PASSWORD_DIR}/auth_setup.out
ELASTIC_LOGIN_FILE=${PASSWORD_DIR}/elastic_login
LOGSTASH_USER=pscheduler_logstash
LOGSTASH_PASSWORD_FILE=${PASSWORD_DIR}/${LOGSTASH_USER}
ENV_FILE="${SCRIPT_DIR}/../.env"
ELASTIC_CONFIG_DIR=/etc/elasticsearch
ELASTIC_CONFIG_FILE=${ELASTIC_CONFIG_DIR}/elasticsearch.yml
ELASTIC_CERT_FILE=${ELASTIC_CONFIG_DIR}/elastic-cert.p12
#Enable security
echo "[Enable elasticsearch security]"
egrep -q "xpack.security.enabled:.*true" $ELASTIC_CONFIG_FILE
if [ $? -eq 0 ]; then
    echo "Elasticsearch security already enabled."
else
    #clear out any old settings
    sed -i '/^xpack.security.*/d' $ELASTIC_CONFIG_FILE
    sed -i '/^.*anonymous:.*/d' $ELASTIC_CONFIG_FILE
    sed -i '/^.*roles:.*/d' $ELASTIC_CONFIG_FILE
    sed -i '/^.*authz_exception:.*/d' $ELASTIC_CONFIG_FILE
    #TODO: DELETE BELOW WHEN WE DROP DOCKER, CAN JUST LISTEN ON LOCALHOST
    sed -i '/^discovery.seed_hosts:.*/d' $ELASTIC_CONFIG_FILE
    sed -i '/^network.host:.*/d' $ELASTIC_CONFIG_FILE
    echo 'discovery.seed_hosts: ["127.0.0.1", "[::1]"]' >> $ELASTIC_CONFIG_FILE 
    echo 'network.host: 0.0.0.0'  >> $ELASTIC_CONFIG_FILE
    #generate elastic certificate
    if [ ! -e $ELASTIC_CERT_FILE ]; then
        /usr/share/elasticsearch/bin/elasticsearch-certutil cert --silent --out $ELASTIC_CERT_FILE --pass ""
        chown elasticsearch:elasticsearch $ELASTIC_CERT_FILE
    fi
    echo "xpack.security.enabled: true" >> $ELASTIC_CONFIG_FILE 
    echo "xpack.security.transport.ssl.enabled: true" >> $ELASTIC_CONFIG_FILE 
    echo "xpack.security.transport.ssl.verification_mode: certificate" >> $ELASTIC_CONFIG_FILE 
    echo "xpack.security.transport.ssl.keystore.path: $ELASTIC_CERT_FILE" >> $ELASTIC_CONFIG_FILE 
    echo "xpack.security.transport.ssl.truststore.path: $ELASTIC_CERT_FILE" >> $ELASTIC_CONFIG_FILE 
    #configure anonymous user permissions
    echo "xpack.security.authc:" >> $ELASTIC_CONFIG_FILE
    echo "  anonymous: " >> $ELASTIC_CONFIG_FILE
    echo "    roles: pscheduler_reader" >> $ELASTIC_CONFIG_FILE
    echo "    authz_exception: true" >> $ELASTIC_CONFIG_FILE
    #apply changes
    systemctl restart elasticsearch.service
fi
echo "[DONE]"
echo ""

#run password setup command, write to tmp file, if works, mv to permanent file
echo "[Generating elasticsearch passwords]"
if [ -e "$PASSWORD_FILE" ]; then
    echo "$PASSWORD_FILE already exists, so not generating new passwords"
else
    mkdir -p $PASSWORD_DIR
    TEMPFILE=$(mktemp)
    chmod 600 $TEMPFILE
    /usr/share/elasticsearch/bin/elasticsearch-setup-passwords auto -b > $TEMPFILE
    if [ $? -eq 0 ]; then
        mv $TEMPFILE $PASSWORD_FILE
        chmod 600 $PASSWORD_FILE #should already be set, just to be sure
    else
        echo "File $PASSWORD_FILE does not exist and password creation failed. Exiting"
        rm $TEMPFILE
        exit 1
    fi
fi
#Get password for elastic user
ELASTIC_PASS=$(grep "PASSWORD elastic = " $PASSWORD_FILE | head -n 1 | sed 's/^PASSWORD elastic = //')
if [ $? -ne 0 ]; then
    echo "Failed to parse password"
    exit 1
elif [ -z "$ELASTIC_PASS" ]; then
    echo "Unable to find elastic password in $PASSWORD_FILE. Exiting."
    exit 1
fi
#Create file with elastic login - overwrite if already there
echo "elastic $ELASTIC_PASS" > $ELASTIC_LOGIN_FILE
chmod 600 $ELASTIC_LOGIN_FILE
echo "[DONE]"
echo ""


# 2. Create roles
echo "[Creating roles]"
${SETUP_DIR}/bin/pselastic roles install -c ${SETUP_DIR}/conf.d --login-file ${ELASTIC_LOGIN_FILE} --max-retries 60 --verbose 
if [ $? -ne 0 ]; then
    echo "Unable to create roles"
    exit 1
fi
echo "[DONE]"
echo ""

#3. Create a user and save the generated password to password_dir
echo "[Creating $LOGSTASH_USER user]"
${SETUP_DIR}/bin/pselastic users install $LOGSTASH_USER -c ${SETUP_DIR}/conf.d --login-file ${ELASTIC_LOGIN_FILE} --max-retries 5 --password-save-dir ${PASSWORD_DIR} --verbose 
if [ $? -ne 0 ]; then
    echo "Unable to create users"
    exit 1
fi
chmod 600 $LOGSTASH_PASSWORD_FILE
LOGSTASH_PASS=$(cat $LOGSTASH_PASSWORD_FILE | head -n 1 | cut -f2 -d " ")
if [ -z "$LOGSTASH_PASS" ]; then
    echo "Unable to find logstash password for elastic"
    exit 1
fi
echo "[DONE]"
echo ""

# 4. Update logstash /etc/sysconfig/logstash to use user/password
echo "[Configure logstash]"
sed -i '/^LOGSTASH_ELASTIC_PASSWORD=/d' /etc/sysconfig/logstash
echo "LOGSTASH_ELASTIC_USER=$LOGSTASH_USER" >> /etc/sysconfig/logstash
echo "LOGSTASH_ELASTIC_PASSWORD=$LOGSTASH_PASS" >> /etc/sysconfig/logstash
echo "[DONE]"
echo ""
