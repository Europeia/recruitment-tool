# Requirements
- python 3.11
  - Ubuntu
    - sudo apt install python3.11 python3.11-dev
    - sudo rm /usr/bin/python3
    - sudo ln -s /usr/bin/python3.11 /usr/bin/python3
- pip
  - Ubuntu
    - sudo apt install python3-pip
- venv
  - Ubuntu
    - sudo apt install python3.11-venv
    - python3 -m venv venv
    - source venv/bin/activate

# Installation
- pip install -r requirements.txt
- mkdir logs
- create a file called settings.json
  - Use settings.json.default as a starting point
  - Fill in correct values for settings.json

# Execution
- python3 main.py