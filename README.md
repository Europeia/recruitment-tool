# NationStates Recruitment Tool

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)  
[![License: GPL-3.0-or-later](https://img.shields.io/badge/license-GPL--3.0--or--later-blue.svg)](https://www.gnu.org/licenses/gpl-3.0.en.html)

## Table of Contents

- [Description](#description)  
- [Features](#features)  
- [Requirements](#requirements)  
- [Installation](#installation)  
- [Configuration](#configuration)  
- [Usage](#usage)  
- [Development & Testing](#development--testing)  
- [Contributing](#contributing)  
- [License](#license)  

---

## Description

A Discord bot that automates NationStates recruitment workflows:

- Queues new nations in real-time  
- Enforces API rate limits  
- Provides slash commands & interactive UIs  
- Tracks recruitment statistics per channel  

---

## Features

- **Background polling** of new nations  
- **Region whitelist** to exclude undesired nations  
- **Interactive modals** for registration & reporting  
- **Recruitment stats** and reports  
- **Robust error handling** and logging  

---

## Requirements

- **OS:** A Debian-based distro
- **Python:** ≥ 3.11  
- **MySQL:** 8.0+ server (or compatible)  
- **Network:** Outbound HTTP access for the NationStates API  

---

## Installation

1. **Clone the repo**  
   ```bash
   git clone https://github.com/Europeia/recruitment-tool.git
   cd recruitment-tool
```

2. **Create & activate a virtual environment**

   ```bash
   python3.11 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Prepare logs directory**

   ```bash
   mkdir -p logs
   ```

---

## Configuration

1. **Copy the example**

   ```bash
   cp settings.json.default settings.json
   ```

2. **Edit `settings.json`**
   Fill in your MySQL credentials, Discord IDs, bot token, etc.

---

## Usage

Run the bot:

```bash
python main.py
```

> **Tip:** Use a process manager (systemd, pm2, etc.) to keep it running in production.

---

## Development & Testing

* **Linting:**

  ```bash
  flake8 .
  ```

* **Type-checking:**

  ```bash
  mypy .
  ```

* **Unit tests:**

  ```bash
  pytest
  ```

---

## Contributing

WIP

---

## License

This project is licensed under the GNU GPL v3.0 (or later).
See [LICENSE](./LICENSE) for the full text.

```
::contentReference[oaicite:0]{index=0}
```
