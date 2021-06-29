#!/bin/bash

SCRIPT_DIR=$(dirname $0)
APP_DIR="$SCRIPT_DIR/../.."
SETUP_DIR="${APP_DIR}/pselastic_setup"
PASSWORD_DIR=/etc/perfsonar/elastic
PASSWORD_FILE=${PASSWORD_DIR}/auth_setup.out
ADMIN_LOGIN_FILE=${PASSWORD_DIR}/elastic_login
LOGSTASH_USER=pscheduler_logstash
LOGSTASH_PASSWORD_FILE=${PASSWORD_DIR}/${LOGSTASH_USER}
ENV_FILE="${SCRIPT_DIR}/../.env"
ELASTIC_CONFIG_DIR=/etc/elasticsearch
ELASTIC_CONFIG_FILE=${ELASTIC_CONFIG_DIR}/elasticsearch.yml
#ELASTIC_CERT_FILE=${ELASTIC_CONFIG_DIR}/elastic-cert.p12
OPENDISTRO_SECURITY_PLUGIN=/usr/share/elasticsearch/plugins/opendistro_security
OPENDISTRO_SECURITY_FILES=${OPENDISTRO_SECURITY_PLUGIN}/securityconfig

systemctl start elasticsearch

# Certificates configurations
# Clear out any config old settings
sed -i '/^opendistro_security.ssl.transport.pemcert_filepath.*/d' $ELASTIC_CONFIG_FILE
sed -i '/^opendistro_security.ssl.transport.pemkey_filepath.*/d' $ELASTIC_CONFIG_FILE
sed -i '/^opendistro_security.ssl.http.pemcert_filepath.*/d' $ELASTIC_CONFIG_FILE
sed -i '/^opendistro_security.ssl.http.pemkey_filepath.*/d' $ELASTIC_CONFIG_FILE
sed -i '/^opendistro_security.authcz.admin_dn.*/d' $ELASTIC_CONFIG_FILE
sed -i '/^opendistro_security.allow_unsafe_democertificates.*/d' $ELASTIC_CONFIG_FILE
sed -i '/^  - CN=kirk.*/d' $ELASTIC_CONFIG_FILE
# Clear out any security script settings
sed -i '/^  - CN=admin.*/d' $ELASTIC_CONFIG_FILE
sed -i '/^opendistro_security.nodes_dn.*/d' $ELASTIC_CONFIG_FILE
sed -i '/^  - CN=localhost.*/d' $ELASTIC_CONFIG_FILE
# Delete demo certificate files
rm ${ELASTIC_CONFIG_DIR}/*.pem
# Generate Opendistro Certificates
# Root CA
openssl genrsa -out ${ELASTIC_CONFIG_DIR}/root-ca-key.pem 2048
openssl req -new -x509 -sha256 -key ${ELASTIC_CONFIG_DIR}/root-ca-key.pem -subj "/CN=localhost/OU=Example/O=Example/C=br" -out ${ELASTIC_CONFIG_DIR}/root-ca.pem -days 180
# Admin cert
openssl genrsa -out ${ELASTIC_CONFIG_DIR}/admin-key-temp.pem 2048
openssl pkcs8 -inform PEM -outform PEM -in ${ELASTIC_CONFIG_DIR}/admin-key-temp.pem -topk8 -nocrypt -v1 PBE-SHA1-3DES -out ${ELASTIC_CONFIG_DIR}/admin-key.pem
openssl req -new -key ${ELASTIC_CONFIG_DIR}/admin-key.pem -subj "/CN=admin" -out ${ELASTIC_CONFIG_DIR}/admin.csr
openssl x509 -req -in ${ELASTIC_CONFIG_DIR}/admin.csr -CA ${ELASTIC_CONFIG_DIR}/root-ca.pem -CAkey ${ELASTIC_CONFIG_DIR}/root-ca-key.pem -CAcreateserial -sha256 -out ${ELASTIC_CONFIG_DIR}/admin.pem -days 180
# Node cert
openssl genrsa -out ${ELASTIC_CONFIG_DIR}/node-key-temp.pem 2048
openssl pkcs8 -inform PEM -outform PEM -in ${ELASTIC_CONFIG_DIR}/node-key-temp.pem -topk8 -nocrypt -v1 PBE-SHA1-3DES -out ${ELASTIC_CONFIG_DIR}/node-key.pem
openssl req -new -key ${ELASTIC_CONFIG_DIR}/node-key.pem -subj "/CN=localhost/OU=node/O=node/L=test/C=br" -out ${ELASTIC_CONFIG_DIR}/node.csr
openssl x509 -req -in ${ELASTIC_CONFIG_DIR}/node.csr -CA ${ELASTIC_CONFIG_DIR}/root-ca.pem -CAkey ${ELASTIC_CONFIG_DIR}/root-ca-key.pem -CAcreateserial -sha256 -out ${ELASTIC_CONFIG_DIR}/node.pem -days 180
# Cleanup
rm ${ELASTIC_CONFIG_DIR}/admin-key-temp.pem ${ELASTIC_CONFIG_DIR}/admin.csr ${ELASTIC_CONFIG_DIR}/node-key-temp.pem ${ELASTIC_CONFIG_DIR}/node.csr
# Add to Java cacerts
keytool -delete -alias node -keystore $JAVA_HOME/lib/security/cacerts -storepass changeit
openssl x509 -outform der -in ${ELASTIC_CONFIG_DIR}/node.pem -out ${ELASTIC_CONFIG_DIR}/node.der
keytool -import -alias node -keystore $JAVA_HOME/lib/security/cacerts -file ${ELASTIC_CONFIG_DIR}/node.der -storepass changeit -noprompt
# Apply new settings
echo "opendistro_security.ssl.transport.pemcert_filepath: node.pem" | tee -a $ELASTIC_CONFIG_FILE > /dev/null
echo "opendistro_security.ssl.transport.pemkey_filepath: node-key.pem" | tee -a $ELASTIC_CONFIG_FILE > /dev/null
echo "opendistro_security.ssl.http.pemcert_filepath: node.pem" | tee -a $ELASTIC_CONFIG_FILE > /dev/null
echo "opendistro_security.ssl.http.pemkey_filepath: node-key.pem" | tee -a $ELASTIC_CONFIG_FILE > /dev/null
echo "opendistro_security.authcz.admin_dn:" | tee -a $ELASTIC_CONFIG_FILE > /dev/null
echo "  - CN=admin" | tee -a $ELASTIC_CONFIG_FILE > /dev/null
echo "opendistro_security.nodes_dn:" | tee -a $ELASTIC_CONFIG_FILE > /dev/null
echo "  - CN=localhost,OU=node,O=node,L=test,C=br" | tee -a $ELASTIC_CONFIG_FILE > /dev/null
# Configure anonymous user permissions
grep "anonymous_auth_enabled: true" $OPENDISTRO_SECURITY_FILES/config.yml
if [ $? -eq 0 ]; then
    echo "Anonymous user permissons already configured."
else
    # Enable anonymous user
    sed -i 's/anonymous_auth_enabled: false/anonymous_auth_enabled: true/g' $OPENDISTRO_SECURITY_FILES/config.yml
    # Creates pscheduler_reader role, with read-only access to he pscheduler indices
    echo | tee -a $OPENDISTRO_SECURITY_FILES/roles.yml > /dev/null
    echo "# Anonymous User Role" | tee -a $OPENDISTRO_SECURITY_FILES/roles.yml > /dev/null
    echo "pscheduler_reader:" | tee -a $OPENDISTRO_SECURITY_FILES/roles.yml > /dev/null
    echo "  reserved: true" | tee -a $OPENDISTRO_SECURITY_FILES/roles.yml > /dev/null
    echo "  index_permissions:" | tee -a $OPENDISTRO_SECURITY_FILES/roles.yml > /dev/null
    echo "    - index_patterns:" | tee -a $OPENDISTRO_SECURITY_FILES/roles.yml > /dev/null
    echo "      - 'pscheduler*'" | tee -a $OPENDISTRO_SECURITY_FILES/roles.yml > /dev/null
    echo "      allowed_actions:" | tee -a $OPENDISTRO_SECURITY_FILES/roles.yml > /dev/null
    echo "      - 'read'" | tee -a $OPENDISTRO_SECURITY_FILES/roles.yml > /dev/null
    # Maps pscheduler_reader role with the anonymous user backend role
    echo | tee -a $OPENDISTRO_SECURITY_FILES/roles_mapping.yml > /dev/null
    echo "pscheduler_reader:" | tee -a $OPENDISTRO_SECURITY_FILES/roles_mapping.yml > /dev/null
    echo '  reserved: true' | tee -a $OPENDISTRO_SECURITY_FILES/roles_mapping.yml > /dev/null
    echo '  backend_roles:' | tee -a $OPENDISTRO_SECURITY_FILES/roles_mapping.yml > /dev/null
    echo '  - "opendistro_security_anonymous_backendrole"' | tee -a $OPENDISTRO_SECURITY_FILES/roles_mapping.yml > /dev/null
fi

# Apply Changes
systemctl restart elasticsearch.service

bash ${OPENDISTRO_SECURITY_PLUGIN}/tools/securityadmin.sh -cd ${OPENDISTRO_SECURITY_PLUGIN}/securityconfig -icl -nhnv -cacert ${ELASTIC_CONFIG_DIR}/root-ca.pem -cert ${ELASTIC_CONFIG_DIR}/admin.pem -key ${ELASTIC_CONFIG_DIR}/admin-key.pem

#run password setup command, write to tmp file, if works, mv to permanent file
echo "[Generating elasticsearch passwords]"
if [ -e "$PASSWORD_FILE" ]; then
    echo "$PASSWORD_FILE already exists, so not generating new passwords"
else
    mkdir -p $PASSWORD_DIR
    TEMPFILE=$(mktemp)
    egrep -v '^[[:blank:]]' "${OPENDISTRO_SECURITY_FILES}/internal_users.yml" | egrep "\:$" | egrep -v '^\_' | sed 's\:\\g' | while read user; do
        PASS=$(tr -dc A-Za-z0-9 </dev/urandom | head -c 20)
        echo "$user $PASS" >> $TEMPFILE
        HASHED_PASS=$(${OPENDISTRO_SECURITY_PLUGIN}/tools/hash.sh -p $PASS | sed -e 's/[&\\/]/\\&/g')
        sed -i -e '/^'$user'\:$/,/[^hash.*$]/      s/\(hash\: \).*$/\1"'$HASHED_PASS'"/' "${OPENDISTRO_SECURITY_FILES}/internal_users.yml"
    done
    mv $TEMPFILE $PASSWORD_FILE
    chmod 600 $PASSWORD_FILE
    bash ${OPENDISTRO_SECURITY_PLUGIN}/tools/securityadmin.sh -cd ${OPENDISTRO_SECURITY_PLUGIN}/securityconfig -icl -nhnv -cacert ${ELASTIC_CONFIG_DIR}/root-ca.pem -cert ${ELASTIC_CONFIG_DIR}/admin.pem -key ${ELASTIC_CONFIG_DIR}/admin-key.pem
fi

#Get password for admin user
# ELASTIC_PASS => ADMIN_PASS
# ELASTIC_LOGIN_FILE => ADMIN_LOGIN_FILE
ADMIN_PASS=$(grep "admin " $PASSWORD_FILE | head -n 1 | sed 's/^admin //')
if [ $? -ne 0 ]; then
    echo "Failed to parse password"
    exit 1
elif [ -z "$ADMIN_PASS" ]; then
    echo "Unable to find admin password in $PASSWORD_FILE. Exiting."
    exit 1
fi

#Create file with admin login - delete if already exists
if [ -f "$ADMIN_LOGIN_FILE" ] ; then
    rm "$ADMIN_LOGIN_FILE"
fi
echo "admin $ADMIN_PASS" | tee -a $ADMIN_LOGIN_FILE > /dev/null
chmod 600 $ADMIN_LOGIN_FILE
echo "[DONE]"
echo ""

# 2. Create roles
echo "[Creating $LOGSTASH_USER role]"
grep "# Pscheduler Logstash" $OPENDISTRO_SECURITY_FILES/roles.yml
if [ $? -eq 0 ]; then
    echo "Role already created"
else
    echo | tee -a $OPENDISTRO_SECURITY_FILES/roles.yml > /dev/null
    echo | tee -a $OPENDISTRO_SECURITY_FILES/roles.yml > /dev/null
    echo "# Pscheduler Logstash" | tee -a $OPENDISTRO_SECURITY_FILES/roles.yml > /dev/null
    echo "pscheduler_logstash:" | tee -a $OPENDISTRO_SECURITY_FILES/roles.yml > /dev/null
    echo "  cluster_permissions:" | tee -a $OPENDISTRO_SECURITY_FILES/roles.yml > /dev/null
    echo "    - 'cluster_monitor'" | tee -a $OPENDISTRO_SECURITY_FILES/roles.yml > /dev/null
    echo "  index_permissions:" | tee -a $OPENDISTRO_SECURITY_FILES/roles.yml > /dev/null
    echo "    - index_patterns:" | tee -a $OPENDISTRO_SECURITY_FILES/roles.yml > /dev/null
    echo "      - 'pscheduler_*'" | tee -a $OPENDISTRO_SECURITY_FILES/roles.yml > /dev/null
    echo "      allowed_actions:" | tee -a $OPENDISTRO_SECURITY_FILES/roles.yml > /dev/null
    echo "      - 'write'" | tee -a $OPENDISTRO_SECURITY_FILES/roles.yml > /dev/null
    echo "      - 'read'" | tee -a $OPENDISTRO_SECURITY_FILES/roles.yml > /dev/null
    echo "      - 'delete'" | tee -a $OPENDISTRO_SECURITY_FILES/roles.yml > /dev/null
    echo "      - 'create_index'" | tee -a $OPENDISTRO_SECURITY_FILES/roles.yml > /dev/null
    echo "      - 'manage'" | tee -a $OPENDISTRO_SECURITY_FILES/roles.yml > /dev/null
    echo "      - 'indices:admin/template/delete'" | tee -a $OPENDISTRO_SECURITY_FILES/roles.yml > /dev/null
    echo "      - 'indices:admin/template/get'" | tee -a $OPENDISTRO_SECURITY_FILES/roles.yml > /dev/null
    echo "      - 'indices:admin/template/put'" | tee -a $OPENDISTRO_SECURITY_FILES/roles.yml > /dev/null
fi
echo "[DONE]"
echo ""

# 3. Create a user and save the generated password to password_dir
echo "[Creating $LOGSTASH_USER user]"
grep "# Pscheduler Logstash" $OPENDISTRO_SECURITY_FILES/internal_users.yml
if [ $? -eq 0 ]; then
    echo "User already created"
else
    # Generate and save logstash password
	PASS=$(tr -dc A-Za-z0-9 </dev/urandom | head -c 20)
    HASHED_PASS=$(${OPENDISTRO_SECURITY_PLUGIN}/tools/hash.sh -p $PASS)
	echo "$LOGSTASH_USER $PASS" | tee -a $PASSWORD_FILE  > /dev/null
	# Add user to internal_users
    echo | tee -a $OPENDISTRO_SECURITY_FILES/internal_users.yml > /dev/null
    echo | tee -a $OPENDISTRO_SECURITY_FILES/internal_users.yml > /dev/null
    echo '# Pscheduler Logstash' | tee -a $OPENDISTRO_SECURITY_FILES/internal_users.yml > /dev/null
    echo 'pscheduler_logstash:' | tee -a $OPENDISTRO_SECURITY_FILES/internal_users.yml > /dev/null
    echo '  hash: "'$HASHED_PASS'"' | tee -a $OPENDISTRO_SECURITY_FILES/internal_users.yml > /dev/null
    echo '  reserved: true' | tee -a $OPENDISTRO_SECURITY_FILES/internal_users.yml > /dev/null
    echo '  attributes:' | tee -a $OPENDISTRO_SECURITY_FILES/internal_users.yml > /dev/null
    echo '    full_name: "pScheduler Logstash User"' | tee -a $OPENDISTRO_SECURITY_FILES/internal_users.yml > /dev/null
    echo '  description: "pscheduler logstash user"' | tee -a $OPENDISTRO_SECURITY_FILES/internal_users.yml > /dev/null
fi
echo "[DONE]"
echo ""

# 4. Map user to role
echo "[Mapping $LOGSTASH_USER user to $LOGSTASH_USER role]"
grep "# Pscheduler Logstash" $OPENDISTRO_SECURITY_FILES/roles_mapping.yml
if [ $? -eq 0 ]; then
    echo "Map already created"
else
    echo | tee -a $OPENDISTRO_SECURITY_FILES/roles_mapping.yml > /dev/null
    echo '# Pscheduler Logstash' | tee -a $OPENDISTRO_SECURITY_FILES/roles_mapping.yml > /dev/null
    echo 'pscheduler_logstash:' | tee -a $OPENDISTRO_SECURITY_FILES/roles_mapping.yml > /dev/null
    echo '  reserved: true' | tee -a $OPENDISTRO_SECURITY_FILES/roles_mapping.yml > /dev/null
    echo '  users:' | tee -a $OPENDISTRO_SECURITY_FILES/roles_mapping.yml > /dev/null
    echo '  - "pscheduler_logstash"' | tee -a $OPENDISTRO_SECURITY_FILES/roles_mapping.yml > /dev/null
fi
echo "[DONE]"
echo ""

bash ${OPENDISTRO_SECURITY_PLUGIN}/tools/securityadmin.sh -cd ${OPENDISTRO_SECURITY_PLUGIN}/securityconfig -icl -nhnv -cacert ${ELASTIC_CONFIG_DIR}/root-ca.pem -cert ${ELASTIC_CONFIG_DIR}/admin.pem -key ${ELASTIC_CONFIG_DIR}/admin-key.pem

#Get password for pscheduler_logstash user
LOGSTASH_PASS=$(grep "pscheduler_logstash " $PASSWORD_FILE | head -n 1 | sed 's/^pscheduler_logstash //')
if [ $? -ne 0 ]; then
    echo "Failed to parse password"
    exit 1
elif [ -z "$LOGSTASH_PASS" ]; then
    echo "Unable to find pscheduler_logstash password in $PASSWORD_FILE. Exiting."
    exit 1
fi

# 5. Update logstash /etc/sysconfig/logstash to use user/password
echo "[Configure logstash]"
grep "LOGSTASH_ELASTIC_USER" /etc/sysconfig/logstash
if [ $? -eq 0 ]; then
    echo "Logstash already configured"
else
	echo "LOGSTASH_ELASTIC_USER=${LOGSTASH_USER}" | tee -a /etc/sysconfig/logstash > /dev/null
	echo "LOGSTASH_ELASTIC_PASSWORD=${LOGSTASH_PASS}" | tee -a /etc/sysconfig/logstash > /dev/null
fi
echo "[DONE]"
echo ""

