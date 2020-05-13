#!/usr/bin/env python3

from utils import *
import string
import secrets

class PSElasticRoleUtil(PSElasticUtil):
    
    def __init__(self):
        self.resource = 'users'
        self.valid_actions = [ "install" ]
        self.password_dir = None
        self.users_exist = {}
        
    def need_user(self, username, user, elastic_url):
        self.log.debug("resource=users action=need_user.start")
        #1. First check if user exists in cache
        if username in self.users_exist:
            self.log.debug("resource=users action=need_user.end msg=User exists in cache")
            return False

        #2. Next check if exists in Elastic
        url = "{0}/_xpack/security/user/{1}".format(elastic_url, username)
        try:
            self.log.debug("resource=users action=check_user.start url={0}".format(url))
            r = requests.get(url=url, auth=self.auth)
            r.raise_for_status()
            #if have a user, then we do not need to create
            if r.json() and r.json().get(username, None):
                self.log.debug("resource=users action=check_user.end url={0} status={1} elastic_reponse={2}".format(url, r.status_code, r.text))
                self.log.debug("resource=users action=need_user.end msg=User exists in elastic")
                self.users_exist[username] = True
                return False
            self.log.debug("resource=users action=check_user.end url={0} status={1} elastic_reponse={2}".format(url, r.status_code, r.text))
        except:
            self.log.error("resource=users action=check_user.error url={0} msg={1}".format(url, sys.exc_info()))
        
        #3. set password if we still need user
        if not user.get("password", None):
            user['password'] = self.generate_password()
        
        return True
        
    def generate_password(self):
        alphabet = string.ascii_letters + string.digits
        password = ''.join(secrets.choice(alphabet) for i in range(32))
        return password
    
    def save_password(self, username, user, elastic_url):
        if not self.password_dir or not user.get("password", None):
            return
        filename = "{0}/{1}".format(self.password_dir, username)
        with open(filename, 'w') as file:
            file.write("{0} {1}".format(username, user["password"]))
    
    def build_arg_parser(self):
        args = super().build_arg_parser()
        args.add_argument('--password-save-dir', dest='password_dir', default=None, type=str, help='A directory to save passwords generated when installing a user.')
        return args
        
    def handle_command(self, args):
        action = args.action[0]
        if action == "install":
            self.password_dir = args.password_dir
            self.load_from_file(
                action, 
                url_path_prefix="_xpack/security/user",
                config_dir=args.config_dir,
                elastic_url=args.elastic_url,
                http_method=requests.post,
                pre_func=self.need_user,
                post_func=self.save_password
            )
        else:
            log.error("Unknown action {0}".format(action))
            sys.exit(1)

'''
Handle when called from command-line
'''
if __name__ == "__main__":
    PSElasticRoleUtil().run()