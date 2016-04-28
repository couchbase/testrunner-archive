import logger
log = logger.Logger.get_logger()
from remote.remote_util import RemoteMachineShellConnection
from membase.api.rest_client import RestConnection
import httplib2
import base64
import requests
import urllib

class ServerInfo():
    def __init__(self,
                 ip,
                 port,
                 ssh_username,
                 ssh_password,
                 ssh_key=''):

        self.ip = ip
        self.ssh_username = ssh_username
        self.ssh_password = ssh_password
        self.port = port
        self.ssh_key = ssh_key


class x509main:
    CHAINCERTFILE = 'chain.pem'
    NODECAKEYFILE = 'pkey.key'
    CACERTFILE = "root.crt"
    CAKEYFILE = "root.key"
    WININSTALLPATH = "C:/Program Files/Couchbase/Server/var/lib/couchbase/"
    LININSTALLPATH = "/opt/couchbase/var/lib/couchbase/"
    MACINSTALLPATH = "/Users/couchbase/Library/Application Support/Couchbase/var/lib/couchbase/"
    DOWNLOADPATH = "/tmp/"
    CACERTFILEPATH = "/tmp/newcerts/"
    CHAINFILEPATH = "inbox"
    GOCERTGENFILE = "gencert.go"
    INCORRECT_ROOT_CERT = "incorrect_root_cert.crt"

    def __init__(self,
                 host=None,
                 method='REST'):

        print host
        if host is not None:
            self.host = host
            self.install_path = self._get_install_path(self.host)
        self.slave_host = ServerInfo('127.0.0.1', 22, 'root', 'couchbase')

    def getLocalIPAddress(self):

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('couchbase.com', 0))
        return s.getsockname()[0]
        '''
        status, ipAddress = commands.getstatusoutput("ifconfig en0 | grep 'inet addr:' | cut -d: -f2 |awk '{print $1}'")
        if '1' not in ipAddress:
            status, ipAddress = commands.getstatusoutput("ifconfig eth0 | grep  -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | awk '{print $2}'")
        return ipAddress
        '''

    def setup_cluster_nodes_ssl(self,servers=[],reload_cert=False):
        for server in servers:
            x509main(server)._setup_node_certificates(reload_cert=reload_cert)

    def _generate_cert(self,servers,root_cn='Root\ Authority',type='go',encryption="",key_length=1024):
        if type == 'go':
            files = []
            cert_file = "./pytests/security/" + x509main.GOCERTGENFILE
            shell = RemoteMachineShellConnection(self.slave_host)
            shell.execute_command("rm -rf /tmp/newcerts")
            shell.execute_command("mkdir /tmp/newcerts")

            shell.execute_command("go run " + cert_file + " -store-to=/tmp/newcerts/root -common-name="+root_cn)
            shell.execute_command("go run " + cert_file + " -store-to=/tmp/newcerts/interm -sign-with=/tmp/newcerts/root -common-name=Intemediate\ Authority")
            for server in servers:
                shell.execute_command("go run " + cert_file + " -store-to=/tmp/newcerts/" + server.ip + " -sign-with=/tmp/newcerts/interm -common-name=" + server.ip + " -final=true")
                shell.execute_command("cat /tmp/newcerts/" + server.ip + ".crt /tmp/newcerts/interm.crt  > " + " /tmp/newcerts/long_chain"+server.ip+".pem")

            shell.execute_command("go run " + cert_file + " -store-to=/tmp/newcerts/incorrect_root_cert -common-name=Incorrect\ Authority")
        elif type == 'openssl':
            files = []
            v3_ca = "./pytests/security/v3_ca.crt"
            shell = RemoteMachineShellConnection(self.slave_host)
            output,error = shell.execute_command("rm -rf /tmp/newcerts")
            log.info ('Output message is {0} and error message is {1}'.format(output,error))
            shell.execute_command("mkdir /tmp/newcerts")
            log.info ('Output message is {0} and error message is {1}'.format(output,error))
            shell.execute_command("openssl genrsa " + encryption + " -out /tmp/newcerts/ca.key " + str(key_length))
            log.info ('Output message is {0} and error message is {1}'.format(output,error))
            output,error = shell.execute_command("openssl req -new -x509  -days 3650 -sha256 -key /tmp/newcerts/ca.key -out /tmp/newcerts/ca.pem -subj '/C=UA/O=My Company/CN=My Company Root CA'")
            log.info ('Output message is {0} and error message is {1}'.format(output,error))

            output, error = shell.execute_command("openssl genrsa " + encryption + " -out /tmp/newcerts/int.key " + str(key_length))
            log.info ('Output message is {0} and error message is {1}'.format(output,error))
            output, error = shell.execute_command("openssl req -new -key /tmp/newcerts/int.key -out /tmp/newcerts/int.csr -subj '/C=UA/O=My Company/CN=My Company Intermediate CA'")
            log.info ('Output message is {0} and error message is {1}'.format(output,error))
            output, error = shell.execute_command("openssl x509 -req -in /tmp/newcerts/int.csr -CA /tmp/newcerts/ca.pem -CAkey /tmp/newcerts/ca.key -CAcreateserial -CAserial /tmp/newcerts/rootCA.srl -extfile ./pytests/security/v3_ca.ext -out /tmp/newcerts/int.pem -days 365 -sha256")
            log.info ('Output message is {0} and error message is {1}'.format(output,error))


            for server in servers:
                output, error = shell.execute_command("openssl genrsa " + encryption + " -out /tmp/newcerts/"+server.ip + ".key " + str(key_length))
                log.info ('Output message is {0} and error message is {1}'.format(output,error))
                output, error= shell.execute_command("openssl req -new -key /tmp/newcerts/" + server.ip + ".key -out /tmp/newcerts/" + server.ip + ".csr -subj '/C=UA/O=My Company/CN=" + server.ip + "'")
                log.info ('Output message is {0} and error message is {1}'.format(output,error))
                output, error = shell.execute_command("openssl x509 -req -in /tmp/newcerts/" + server.ip + ".csr -CA /tmp/newcerts/int.pem -CAkey /tmp/newcerts/int.key -CAcreateserial -CAserial /tmp/newcerts/intermediateCA.srl -out /tmp/newcerts" + server.ip + ".pem -days 365 -sha256")
                log.info ('Output message is {0} and error message is {1}'.format(output,error))
                output, error = shell.execute_command("openssl x509 -req -days 300 -in /tmp/newcerts/" + server.ip + ".csr -CA /tmp/newcerts/int.pem -CAkey /tmp/newcerts/int.key -set_serial 01 -out /tmp/newcerts/" + server.ip + ".pem")
                log.info ('Output message is {0} and error message is {1}'.format(output,error))
                output, error = shell.execute_command("cat /tmp/newcerts/" + server.ip + ".pem /tmp/newcerts/int.pem > /tmp/newcerts/long_chain"+server.ip+".pem")
                log.info ('Output message is {0} and error message is {1}'.format(output,error))

            output, error = shell.execute_command("cp /tmp/newcerts/ca.pem /tmp/newcerts/root.crt")
            log.info ('Output message is {0} and error message is {1}'.format(output,error))



    def _reload_node_certificate(self,host):
        rest = RestConnection(host)
        api = rest.baseUrl + "node/controller/reloadCertificate"
        http = httplib2.Http()
        status, content = http.request(api, 'POST', headers=self._create_rest_headers('Administrator','password'))
        #status, content, header = rest._http_request(api, 'POST')
        print status
        print content
        return status, content

    def _get_install_path(self,host):
        shell = RemoteMachineShellConnection(host)
        os_type = shell.extract_remote_info().distribution_type
        log.info ("OS type is {0}".format(os_type))
        if os_type == 'windows':
            install_path = x509main.WININSTALLPATH
        elif os_type == 'Mac':
            install_path = x509main.MACINSTALLPATH
        else:
            install_path = x509main.LININSTALLPATH

        return install_path

    def _create_inbox_folder(self,host):
        shell = RemoteMachineShellConnection(self.host)
        final_path = self.install_path + x509main.CHAINFILEPATH
        shell.create_directory(final_path)

    def _delete_inbox_folder(self):
        shell = RemoteMachineShellConnection(self.host)
        final_path = self.install_path + x509main.CHAINFILEPATH
        shell = RemoteMachineShellConnection(self.host)
        os_type = shell.extract_remote_info().distribution_type
        log.info ("OS type is {0}".format(os_type))
        shell.delete_file(final_path , "root.crt")
        shell.delete_file(final_path , "chain.pem")
        shell.delete_file(final_path , "pkey.key")
        if os_type == 'windows':
            final_path = '/cygdrive/c/Program\ Files/Couchbase/Server/var/lib/couchbase/inbox'
            shell.execute_command('rm -rf ' + final_path)
        else:
            shell.execute_command('rm -rf ' + final_path)

    def _copy_node_key_chain_cert(self,host,src_path,dest_path):
        shell = RemoteMachineShellConnection(host)
        shell.copy_file_local_to_remote(src_path,dest_path)

    def _setup_node_certificates(self,chain_cert=True,node_key=True,reload_cert=True):
        self._create_inbox_folder(self.host)
        src_chain_file = "/tmp/newcerts/long_chain" + self.host.ip + ".pem"
        dest_chain_file = self.install_path + x509main.CHAINFILEPATH + "/" + x509main.CHAINCERTFILE
        src_node_key = "/tmp/newcerts/" + self.host.ip + ".key"
        dest_node_key = self.install_path + x509main.CHAINFILEPATH + "/" + x509main.NODECAKEYFILE
        if chain_cert:
            self._copy_node_key_chain_cert(self.host, src_chain_file, dest_chain_file)
        if node_key:
            self._copy_node_key_chain_cert(self.host, src_node_key, dest_node_key)
        if reload_cert:
            status, content = self._reload_node_certificate(self.host)
            return status, content


    def _create_rest_headers(self,username="Administrator",password="password"):
        authorization = base64.encodestring('%s:%s' % (username,password))
        return {'Content-Type': 'application/octet-stream',
            'Authorization': 'Basic %s' % authorization,
            'Accept': '*/*'}


    def _rest_upload_file(self,URL,file_path_name,username=None,password=None):
        data  =  open(file_path_name, 'rb').read()
        http = httplib2.Http()
        status, content = http.request(URL, 'POST', headers=self._create_rest_headers(username,password),body=data)
        print URL
        print status
        print content
        return status, content


    def _upload_cluster_ca_certificate(self,username,password):
        rest = RestConnection(self.host)
        url = "controller/uploadClusterCA"
        api = rest.baseUrl + url
        self._rest_upload_file(api,"/tmp/newcerts/" + x509main.CACERTFILE,"Administrator",'password')


    def _validate_ssl_login(self,host=None,port=18091,username='Administrator',password='password'):
        key_file = x509main.CACERTFILEPATH + x509main.CAKEYFILE
        cert_file = x509main.CACERTFILEPATH + x509main.CACERTFILE
        if host is None:
            host = self.host.ip
        try:
            r = requests.get("https://"+host+":18091",verify=cert_file)
            if r.status_code == 200:
                header = {'Content-type': 'application/x-www-form-urlencoded'}
                params = urllib.urlencode({'user':'{0}'.format(username), 'password':'{0}'.format(password)})
                r = requests.post("https://"+host+":18091/uilogin",data=params,headers=header,verify=cert_file)
                return r.status_code
        except Exception, ex:
            print "into exception"
            print ex
            return 'error'

    def _get_cluster_ca_cert(self):
        rest = RestConnection(self.host)
        api = rest.baseUrl + "pools/default/certificate?extended=true"
        status, content, header = rest._http_request(api, 'GET')
        return status, content, header

    def setup_master(self,user='Administrator',password='password'):
        x509main(self.host)._upload_cluster_ca_certificate(user,password)
        x509main(self.host)._setup_node_certificates()
