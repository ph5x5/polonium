#! python3
# IMPORTS
import argparse
import logging
import os
import subprocess
import platform
import yaml
import io
import jinja2
import tempfile
import random
import socket
import fileinput
import time




# CLASSES
class main(object):
    def __init__(self):
        self.parameters = {
            'automated': False,
            'environment': None,
            'distribution': None,
            'case_template': None,
            'output_file': None,
            'exception_path': None,
            'reports_path': None,
            'output_language': 'python',
            'hub': None,
            'browsers': [],
            'reports': [],
            'reporters': [],
            'gui': None,
            'variables': []
        }
        

        Init().parse_arguments(self)     
        Init().get_environment(self)
        Init().check_environment(self.parameters['environment'], self.parameters['distribution'], self.parameters['automated'])

        Parser().process_template(self, self.parameters['case_template'])
        Docker().launch_environment(self.parameters['hub'], self.parameters['browsers'], self.parameters['gui'])
        Infra().run_command_console('Launching test', 'python -u "./output.py"')
        Docker().clear_environment()



class Infra(object):
    def fail_with_error(self, text):
        logging.critical(text)
        exit(1)

    def run_command_console(self, name, command):
        logging.info('{}..'.format(name))
        try:
            subprocess.call(command, shell = True)
        except IOError:
            self.fail_with_error('Step "{}" failed due to error: {}'.format(name, IOError))



class CheckSoftware(object):
    def check_docker(self, init, env):
        if env == 'linux':
            check_command = 'which'
        else:
            check_command = 'where'
        rc = subprocess.call([check_command, 'docker'], stdout = subprocess.DEVNULL, stderr = subprocess.STDOUT)
        if rc == 0:
            init.installed_list['docker'] = True
            return True
        else:
            return False



class InstallSoftware(object):
    def install_docker(self, init, env, distribution, automated, user):
        if automated == False:
            confirm = self.get_input('Docker is not found. Please confirm installation (y)')
        else:
            confirm = 'y'
        
        if confirm == 'y':
            try:
                if env == 'windows':
                    temp_dir = tempfile.gettempdir()
                    self.run_command('Downloading Docker installation package', 'powershell Invoke-WebRequest -Uri "https://download.docker.com/win/stable/Docker%20for%20Windows%20Installer.exe" -OutFile "{}}\DockerInstaller.exe"'.format(temp_dir))
                    if automated == True:
                        self.run_command('Installing Docker', '{}\DockerInstaller.exe install --quiet'.format(temp_dir))
                    else:
                        self.run_command('Installing Docker', '{}\DockerInstaller.exe'.format(temp_dir))
                    self.run_command('Removing temporary file', 'powershell Remove-Item -Path "{}\DockerInstaller.exe" -Force'.format(temp_dir))
                    if CheckSoftware().check_docker(init, env) == False:
                        print('\r')
                        Infra().fail_with_error('Failed to install Docker')
                elif env == 'linux':
                    update_text = 'Updating repository'
                    if (distribution == 'centos') or (distribution == 'redhat'):
                        self.run_command(update_text, 'sudo yum check-update')
                    elif (distribution == 'ubuntu') or (distribution == 'debian'):
                        self.run_command(update_text, 'sudo apt-get update')
                    self.run_command('Installing docker', 'curl -fsSL https://get.docker.com/ | sh')
                    if automated == False:
                        user = self.get_input('Please provide the user name to add to "docker" group')
                    self.run_command('Adding {} to the docker group'.format(user), 'sudo usermod -aG docker {}'.format(user))
                    self.run_command('Starting docker', 'sudo systemctl start docker')
                    self.run_command('Checking docker status', 'sudo systemctl status docker')
                logging.info('Docker installed successfully')
            except Exception as e:
                Infra().fail_with_error('Error installing docker: {}'.format(e))
        else:
            Infra().fail_with_error('Docker is needed to run the polonium!')

        return True


    def run_command(self, name, command):
        logging.info('{}..'.format(name))
        try:
            output = os.popen(command).read()
        except IOError:
            Infra().fail_with_error('Step "{}" failed due to error: {}'.format(name, IOError))

        return output


    def get_input(self, text):
        result = None
        while not result:
            try:
                result = input('{}: '.format(text))
            except SyntaxError:
                result = None
                logging.info('Please provide a valid input')
        
        return result



class Init(object):
    def get_environment(self, main):
        if os.name == "nt":
            main.parameters['environment'] = "windows"
        else:
            main.parameters['environment'] = 'linux'
            distribution = platform.linux_distribution()[0]
            if 'Ubuntu' in distribution:
                main.parameters['distribution'] = 'ubuntu'
            elif 'CentOS' in distribution:
                main.parameters['distribution'] = 'centos'
            elif 'debian' in distribution:
                main.parameters['distribution'] = 'debian'
            elif 'RedHat' in distribution:
                main.parameters['distribution'] = 'redhat'
            else:
                Infra().fail_with_error('This linux distribution is not supported on {}.'.format(distribution))


    def parse_arguments(self, main):
        # Accepting arguments
        parser = argparse.ArgumentParser(description = 'Script converts the yaml test case to java Selenium Webdriver code.')

        parser.add_argument('--case', help = 'Input yaml test case path')
        parser.add_argument('--uri', help = 'Application URI to test. Overrides one that was pointed in case')
        parser.add_argument('--hub', help = 'Selenium server URI, default: server will be launched in local containers')
        parser.add_argument('--out', help = 'Name of the output file, default: output.py')
        parser.add_argument('--loglevel', help = 'Python log level, default: logging.INFO')
        parser.add_argument('--auto', help = 'Run in automated mode', action = 'store_true')
        parser.add_argument('--gui', help = 'Run test containers in gui mode. Only works if hub is not pointed.', action = 'store_true')
        parser.add_argument('--variables', help = 'Set of variables in format "<var>=<value>;" to override predefined in other places')

        args = parser.parse_args()

        # Validating arguments
        if args.auto != None:
            logging.info('Test would be run in automated mode. No user input expected.')
            main.automated = True
        else:
            main.automated = False

        if args.loglevel != None:
            logging.getLogger().setLevel(eval(args.loglevel))
            logging.info('Log level set to: ' + args.loglevel)
        else:
            logging.getLogger().setLevel(logging.INFO)

        if args.case != None:
            logging.info('Test case: ' + args.case)
            main.parameters['case_template'] = args.case
        else:
            Infra().fail_with_error('Test case is not provided!')

        if args.uri != None:
            logging.info('URI: ' + args.uri)
            applicationUri = args.uri
        else:
            applicationUri = ''

        if args.hub != None:
            logging.info('Selenium address: ' + args.hub)
            main.parameters['hub'] = args.hub
        else:
            logging.info('Hub parameters are not provided. Will launch containers myself.')
            main.parameters['hub'] = 'launch_placeholder'

        if args.out != None:
            logging.info('Output will be saved to: ' + args.out + '\n')
            outputFile = args.out
        else:
            outputFile = 'test.py'

        if args.gui != False:
            logging.info('The test would be launched in graphical mode.')
            main.parameters['gui'] = True
        else:
            main.parameters['gui'] = False

        if args.variables != None:
            variables = args.variables.split(';')
            for variable in variables:
                var_array = variable.split('=')
                var = {'name': var_array[0], 'value': var_array[1]}
                main.parameters['variables'].append(dict(var))


    def check_environment(self, env, distribution, automated):
        self.installed_list = {
            'docker': False
        }

        CheckSoftware().check_docker(self, env)
        if self.installed_list['docker'] == True:
            logging.debug('Docker is already installed')
            docker_result = True
        else:
            docker_result = False
            if automated == True:
                user = 'root'
            else:
                user = None
            docker_result = InstallSoftware().install_docker(self, env, distribution, automated, user)

        if docker_result == True:
            return True
        else:
            Infra().fail_with_error('Failed to install components required')


    def init_reporters(self, reports, main):
        for report in reports:
            config = './plugins/reports/{}.yaml'.format(report)
            main.parameters['reporters'].append(self.make_reporter(config))

    
    def make_reporter(self, config):
        reporter = Reporter(config)
        return reporter



class Parser(object):
    def process_config(self, main, config_data):
        try:
            main.parameters['output_file'] = config_data['general']['output_file']
            main.parameters['exception_path'] = config_data['general']['exception_path']
            main.parameters['reports_path'] = config_data['general']['reports_path']
        except Exception as e:
            Infra().fail_with_error("Config file doesn't contain {} parameter".format(e))


    def process_template(self, main, case_template):
        try:
            with open(case_template) as f:
                case_config = (f.read().splitlines()[0]).split(': ')[1]
        except FileNotFoundError:
            Infra().fail_with_error("Test template file {} doesn't exist".format(case_template))
        try:
            config_data = yaml.load(open(case_config), Loader = yaml.FullLoader)
            for variable in main.parameters['variables']:
                config_data[variable['name']] = variable['value']
            self.process_config(main, config_data)
        except FileNotFoundError:
            Infra().fail_with_error("Configuration file {} pointed in {} doesn't exist".format(case_config, case_template))
        with open(case_template) as file:
            template = jinja2.Template(file.read())
            case = yaml.load(template.render(config_data), Loader = yaml.FullLoader)
        self.process_case(main, case)
        

    def process_case(self, main, case):
        self.main = main
        self.case = case
        self.lines = ''

        self.import_parameter('browsers', 'browsers')
        self.import_parameter('reports', 'reports')

        Init().init_reporters(main.parameters['reports'], main)
        strings_file = './plugins/lang/{}.yaml'.format(main.parameters['output_language'])


        try:
            self.strings = yaml.load(open(strings_file), Loader = yaml.FullLoader)
        except Exception as e:
            Infra().fail_with_error('Can\'t load the configuration file "{}". Error: "{}"'.format(strings_file, e))

        for string_import in self.strings['headers']['imports']:
            self.add_line(string_import['string'], string_import['indent'])
        self.add_blank()

        i = 0
        for browser in main.parameters['browsers']:
            for string_init in self.strings['headers']['init']:
                if main.parameters['output_language'] == 'python':
                    if string_init['name'] == 'set_remote':
                        if main.parameters['hub'] == 'launch_placeholder':
                            hub = browser + '_placeholder'
                        else:
                            hub = main.parameters['hub']
                        self.add_line(string_init['string'].format(browserId = i, hub = hub, browserName = browser), string_init['indent'])
            i += 1
        self.add_blank()

        i = 0
        for browser in main.parameters['browsers']:
            self.process_steps(self.case['steps'], 0, i, browser, main.parameters['reporters'])
            self.add_blank()
            i += 1
        
        with open('output.py', 'w') as output_file:
            output_file.write(self.lines)
                
    
    def process_steps(self, steps, indent, browserId, browser, reporters):
        for reporter in reporters:
            reporter.headers(self, browser)
        strings = self.strings['steps']
        for step in steps:
            step_name = list(step.keys())[0]
            parameters = { 'browserId': browserId }
            if step[step_name] is not None:
                for parameter in step[step_name]:
                    parameters[parameter] = step[step_name][parameter]
            for reporter in reporters:
                reporter.start(step_name, self, parameters)
            for string in strings[step_name]:
                self.add_line(string['string'].format(**parameters), indent + string['indent'])
            for reporter in reporters:
                reporter.stop(step_name, self, parameters)
        self.add_line('browser{}.close()'.format(browserId), indent)
        for reporter in reporters:
            reporter.footers(self)
   
            
    def import_parameter(self, parameter, name):
        try:
            self.main.parameters[name] = self.case[name]
        except Exception as e:
            Infra().fail_with_error('Check the "{}" parameter in "{}". It must be present and contain list of {}. Error: "{}"'
                .format(parameter, self.main.parameters['case_template'], name, e))


    def add_line(self, text, indent):
        indent_string = ''
        newline = '\n'
        for i in range(0, indent):
            indent_string += '  '
        self.lines += indent_string + text + newline


    def add_blank(self):
        self.lines += '\n'



class Reporter(object):
    config_file = ''
    config = None
    

    def __init__(self, config):
        self.config_file = config
        self.config = yaml.load(open(self.config_file), Loader = yaml.FullLoader)

    
    def headers(self, parser, browser):
        for header in self.config['headers']:
            string = (self.config['infrastructure']['string_start'] + header['string'] + self.config['infrastructure']['string_end']).format(browser = browser)
            parser.add_line(string, 0)
        parser.add_blank()


    def start(self, step_name, parser, parameters):
        string = (self.config['infrastructure']['string_start'] + self.config['steps'][step_name]['string'] + self.config['infrastructure']['string_end']).format(**parameters)
        parser.add_line(string, 0)


    def footers(self, parser):
        for footer in self.config['footers']:
            string = self.config['infrastructure']['string_start'] + footer['string'] + self.config['infrastructure']['string_end']
            parser.add_line(string, 0)


    def stop(self, step_name, parser, parameters):
        if 'string_after' in self.config['steps'][step_name]:
            string = (self.config['infrastructure']['string_start'] + self.config['steps'][step_name]['string_after'] + self.config['infrastructure']['string_end']).format(**parameters)
            parser.add_line(string, 0)
        parser.add_blank()



class Docker(object):
    containers = []


    def launch_environment(self, hub, browsers, gui):
        if hub == 'launch_placeholder':
            for browser in browsers:
                port = self.get_free_port()
                if gui == True:
                    gui_port = self.get_free_port()
                    gui_string = '-debug'
                    gui_port_string = ' -p {}:5900'.format(gui_port)
                    gui_console_string = ' and on VNC port: {}'.format(gui_port)
                else:
                    gui_string = ''
                    gui_port_string = ''
                    gui_console_string = ''
                image = 'selenium/standalone-{}{}'.format(browser, gui_string)
                command = 'docker run -d -p {}:4444{} -v /dev/shm:/dev/shm {}'.format(port, gui_port_string, image)
                container_id = InstallSoftware().run_command('Launching {} container on port: {}{}'.format(browser, port, gui_console_string), command)
                with fileinput.FileInput('output.py', inplace = True) as file:
                    for line in file:
                        print(line.replace('{}_placeholder'.format(browser), 'http://127.0.0.1:{}/wd/hub'.format(port)), end = '')
                time.sleep(10)
                self.containers.append(container_id)


    def clear_environment(self):
        for container in self.containers:
            InstallSoftware().run_command(
                'Stopping container with id: {}'.format(container),
                'docker stop {}'.format(container)
            )
            InstallSoftware().run_command(
                'Removing container with id: {}'.format(container),
                'docker rm {}'.format(container)
            )


    def get_free_port(self):
        bound = False
        while bound != True:
            port = 30000 + random.randint(0, 20000)
            if self.port_in_use(port) == False:
                bound = True
        return port

                
    def port_in_use(self, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', port)) == 0




# BODY
if __name__ == '__main__':
    main()
