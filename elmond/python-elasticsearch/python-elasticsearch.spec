%global tarball_name elasticsearch

Name:           python-elasticsearch
Version:        7.0.5
Release:        2%{?dist}
Summary:        Client for Elasticsearch

License:        ASL 2.0
URL:            https://github.com/elasticsearch/elasticsearch-py
Source0:        https://pypi.io/packages/source/e/%{tarball_name}/%{tarball_name}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires:  python%{python3_pkgversion}-devel
BuildRequires:  python%{python3_pkgversion}-setuptools

%global _description\
Low level client for Elasticsearch. It's goal is to provide common ground\
for all Elasticsearch-related code in Python. The client's features include:\
\
- Translating basic Python data types to and from json\
- Configurable automatic discovery of cluster nodes\
- Persistent connections\
- Load balancing (with pluggable selection strategy) across all available nodes\
- Failed connection penalization (time based - failed connections won't be\
  retried until a timeout is reached)\
- Thread safety\
- Pluggable architecture

%description %_description


%package -n python%{python3_pkgversion}-%{tarball_name}
Summary:        Python 3 Client for Elasticsearch
License:        ASL 2.0
Requires:       python3-urllib3

%description -n python%{python3_pkgversion}-%{tarball_name}
Low level client for Elasticsearch. It's goal is to provide common ground
for all Elasticsearch-related code in Python. The client's features include:

- Translating basic Python data types to and from json
- Configurable automatic discovery of cluster nodes
- Persistent connections
- Load balancing (with pluggable selection strategy) across all available nodes
- Failed connection penalization (time based - failed connections won't be
  retried until a timeout is reached)
- Thread safety
- Pluggable architecture

%prep
%setup -qn %{tarball_name}-%{version}
rm -fr %{tarball_name}.egg-info

%build
%py3_build

%install
%py3_install

%check
# * missing requirements for tests: python-pyaml
# * tests are not included in the tarball, we would have to add an extra
# source for them
# * https://github.com/elastic/elasticsearch-py/tree/master/test_elasticsearch
# also notes that "The tests also rely on a checkout of elasticsearch
# repository existing on the same level", and it looks like they also
# require a running elasticsearch server

%files -n python%{python3_pkgversion}-elasticsearch
%{python3_sitelib}/%{tarball_name}
%{python3_sitelib}/%{tarball_name}-%{version}-py3.?.egg-info
%doc README
%license LICENSE

%changelog
* Fri Jul 30 2021 Daniel Neto <daniel.neto@rnp.br> - 7.0.5-2
- Removing python2 package

* Fri Nov 15 2019 Steve Traylen <steve.traylen@cern.ch> - 7.0.5-2
- Adapt for EPEL 8

* Wed Nov 13 2019 Steve Traylen <steve.traylen@cern.ch> - 7.0.5-1
- Latest upstream 7.0.5.

* Thu Oct 03 2019 Miro Hrončok <mhroncok@redhat.com> - 7.0.0-4
- Rebuilt for Python 3.8.0rc1 (#1748018)

* Mon Aug 19 2019 Miro Hrončok <mhroncok@redhat.com> - 7.0.0-3
- Rebuilt for Python 3.8

* Fri Jul 26 2019 Fedora Release Engineering <releng@fedoraproject.org> - 7.0.0-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_31_Mass_Rebuild

* Mon May 06 2019 Steve Traylen <steve.traylen@cern.ch> - 7.0.0-1
- Latest upstream 7.0.0.

* Sat Feb 02 2019 Fedora Release Engineering <releng@fedoraproject.org> - 6.3.1-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_30_Mass_Rebuild

* Tue Nov 20 2018 Steve Traylen <steve.traylen@cern.ch> - 6.3.1-1
- Latest upstream 6.3.1.

* Thu Sep 27 2018 Piotr Popieluch <piotr1212@gmail.com> - 2.4.0-9
- Remove Python2 supbackage

* Sat Jul 14 2018 Fedora Release Engineering <releng@fedoraproject.org> - 2.4.0-8
- Rebuilt for https://fedoraproject.org/wiki/Fedora_29_Mass_Rebuild

* Tue Jun 19 2018 Miro Hrončok <mhroncok@redhat.com> - 2.4.0-7
- Rebuilt for Python 3.7

* Fri Feb 09 2018 Fedora Release Engineering <releng@fedoraproject.org> - 2.4.0-6
- Rebuilt for https://fedoraproject.org/wiki/Fedora_28_Mass_Rebuild

* Sat Aug 19 2017 Zbigniew Jędrzejewski-Szmek <zbyszek@in.waw.pl> - 2.4.0-5
- Python 2 binary package renamed to python2-elasticsearch
  See https://fedoraproject.org/wiki/FinalizingFedoraSwitchtoPython3

* Thu Jul 27 2017 Fedora Release Engineering <releng@fedoraproject.org> - 2.4.0-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Mass_Rebuild

* Sun Mar 12 2017 Piotr Popieluch <piotr1212@gmail.com> - 2.4.0-3
- Update python thrift requires

* Sat Feb 11 2017 Fedora Release Engineering <releng@fedoraproject.org> - 2.4.0-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_26_Mass_Rebuild

* Wed Dec 28 2016 Adam Williamson <awilliam@redhat.com> - 2.4.0-1
- Update to 2.4.0 (needed for latest elastic-curator)
- Document missing tests

* Mon Dec 19 2016 Miro Hrončok <mhroncok@redhat.com> - 2.3.0-4
- Rebuild for Python 3.6

* Tue Jul 19 2016 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.3.0-3
- https://fedoraproject.org/wiki/Changes/Automatic_Provides_for_Python_RPM_Packages

* Wed Jun 15 2016 Orion Poplawski <orion@cora.nwra.com> - 2.3.0-2
- Drop %%py3dir and use new macros

* Wed Jun 08 2016 Piotr Popieluch <piotr1212@gmail.com> - 2.3.0-1
- Update to 2.3.0

* Wed Jun 08 2016 Piotr Popieluch <piotr1212@gmail.com> - 2.0.0-4
- Readd python-rullib dependency, rpmlint Error needs to be ignored #1344121

* Thu Feb 04 2016 Fedora Release Engineering <releng@fedoraproject.org> - 2.0.0-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_24_Mass_Rebuild

* Wed Nov 04 2015 Robert Kuska <rkuska@redhat.com> - 2.0.0-2
- Rebuilt for Python3.5 rebuild

* Wed Oct 14 2015 Daniel Bruno <dbruno@fedoraproject.org> - 2.0.0-1
- Elasticsearch 2.0.0 version release

* Tue Sep 22 2015 Daniel Bruno <dbruno@fedoraproject.org> - 1.7.0-1
- Upgrade to 1.7.0

* Thu Jun 18 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.4.0-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_23_Mass_Rebuild

* Thu May 14 2015 Piotr Popieluch <piotr1212@gmail.com> - 1.4.0-2
- Add python3 module
- Remove trailing whitespace
- Remove deprecated group tag
- Move license from %%doc to %%license
- Remove deprecated rm -rf buildroot
- fix rpmlint Error: explicit-lib-dependency python-urllib3

* Tue Apr 07 2015 Alan Pevec <apevec@fedoraproject.org> - 1.4.0-1
- Upgrade to 1.4.0 version

* Sat Jun 07 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.0.0-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Mon Apr 14 2014 Daniel Bruno <dbruno@fedoraproject.org> - 1.0.0-1
- Upgrade to 1.0.0 version

* Tue Nov 26 2013 Daniel Bruno <dbruno@fedoraproject.org> - 0.4.3-1
- First RPM release
