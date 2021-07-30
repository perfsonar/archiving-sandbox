# Makefile for perfSONAR Elmond
#
PACKAGE=perfsonar-elmond
ROOTPATH=/usr/lib/perfsonar/elmond
CONFIGPATH=/etc/perfsonar/elmond
PERFSONAR_AUTO_VERSION=4.4.0
PERFSONAR_AUTO_RELNUM=0.0.a1
VERSION=${PERFSONAR_AUTO_VERSION}
RELEASE=${PERFSONAR_AUTO_RELNUM}
DC_CMD_BASE=docker-compose
DC_CMD=${DC_CMD_BASE} -p ${PACKAGE}

centos7:
	mkdir -p ./artifacts/centos7
	${DC_CMD} -f docker-compose.build.yml up --build --no-start centos7
	docker cp ${PACKAGE}_centos7_1:/root/rpmbuild/SRPMS ./artifacts/centos7/SRPMS
	docker cp ${PACKAGE}_centos7_1:/root/rpmbuild/RPMS/noarch ./artifacts/centos7/RPMS

dist:
	mkdir /tmp/${PACKAGE}-${VERSION}.${RELEASE}
	cp -rf ./conf ./elmond ./systemd ./Makefile ./perfsonar-elmond.spec /tmp/${PACKAGE}-${VERSION}.${RELEASE}
	tar czf ${PACKAGE}-${VERSION}.${RELEASE}.tar.gz -C /tmp ${PACKAGE}-${VERSION}.${RELEASE}
	rm -rf /tmp/${PACKAGE}-${VERSION}.${RELEASE}

install:
	mkdir -p ${ROOTPATH}
	mkdir -p ${CONFIGPATH}
	cp -r elmond/* ${ROOTPATH}
	cp -r conf/* ${CONFIGPATH}