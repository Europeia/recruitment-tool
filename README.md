# Recruitment Tool

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)  
[![License: GPL-3.0-or-later](https://img.shields.io/badge/license-GPL--3.0--or--later-blue.svg)](https://www.gnu.org/licenses/gpl-3.0.en.html)

A Discord bot that automates NationStates recruitment: queues new nations, enforces rate limits, and a Discord user interface.

---

## Requirements

- **Python:** 3.11 or later  
- **MySQL:** 8.0+ server (or compatible)  
- **Network:** Outbound HTTP to `nationstates.net`

---

## Installation

### 1. Clone the repo
```bash
git clone https://github.com/Europeia/recruitment-tool.git
cd recruitment-tool
````

### 2. Create & activate a virtual environment

* **Debian/Ubuntu, Fedora, or other Linux:**

  ```bash
  python3.11 -m venv venv
  source venv/bin/activate
  ```
* **macOS (with Homebrew):**

  ```bash
  brew install python@3.11
  python3.11 -m venv venv
  source venv/bin/activate
  ```
* **Windows (PowerShell):**

  ```powershell
  py -3.11 -m venv venv
  .\venv\Scripts\Activate.ps1
  ```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Configuration

1. Copy the example:

   ```bash
   cp settings.json.default settings.json
   ```
   
2. **Edit `settings.json`**  
   Replace placeholder values and adjust as needed:

   - **MySQL**  
      `dbHost`, `dbPort`, `dbUser`, `dbPassword`, `dbName`  
   - **NationStates API**  
      `operator`  
   - **Discord IDs**  
      `guildId`, `recruitChannelId`, `reportChannelId`, `recruitRoleId`, `statusMessageId`  
   - **Bot token**  
      `botToken`  
   - **Polling & rate limits**  
      `pollingRate`, `periodMax`  
   - **Region exceptions**  
      `recruitmentExceptions` (array of region keys)  

---

## Usage

Run the bot in your active virtual environment:

```bash
python3 main.py
```

* **User Interface:**

  * `/register` to register a channel
  * Buttons to recruit, register, or view reports

---

## License

GPL-3.0-or-later. See [LICENSE.md](./LICENSE.md).
