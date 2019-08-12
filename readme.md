# **Polonium**
Polonium automates the browser UI and has simple synyax and easy to run just from the box.<br />
It has simple YAML syntax and allows to write custom output and language plugins. For now it has only console output.<br />
For now it converts the YAML steps to the python code and launches the result test script on the selenium webdriver server, also it launches the neede containers automatically.

## How it works:
1. Checks environment
2. Parses the YAML/jinja2 case template and updates it with the variables from the linked YAML configuration file
3. Renders the python script based on the pointed steps
4. Launches the browser containers if needed
5. Runs the script on the hub/local containers
6. Outputs the result via the report plugins
7. Cleans after itself

**As an example you can use the example test case. The syntax is VERY simple:**
> ./cases/example.yaml

**It could be launched with command. YES! It's as simple as this:**
> python -u './polonium.py' --case './cases/example.yaml'

## Command line parameters:
- --case      - the case file with browser actions (mandatory)
- --uri       - the URI to override the pointed in case one
- --hub       - the Selenium Hub uri, if not pointed - local containers would be launched
- --loglevel  - set python loglevel
- --auto      - silent/quiet mode
- --gui       - run containers in graphical debug mode with VNC port open, doesn't work together with --hub option
- --variables - Set of variables in format "{var}={value};" to override predefined in other places

## Specs:
- **OS**: Windows/Linux
- **Requirements**: Python3, Docker (installs on the first launch), selenium module
- **Supported browsers**: Chrome, Firefox (launched in headless mode in containers)

## Troubleshooting:
1. **No selenium module:** pip install selenium (pip3 install selenium)
2. **Module 'yaml' has no attribute 'FullLoader':** update your version of pyyaml module

## Info
Detailed documentation would be posted at wiki page soon.<br />
It's currently only a draft version and has only limited functionality which would be constantly improved.
