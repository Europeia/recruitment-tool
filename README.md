# Asperta
Named after a prolific early Europeian recruiter, Asperta is a multitenant Discord based recruitment tool for [NationStates](https://www.nationstates.net/). A guide for both users and administrators is available in [dispatch form](https://www.nationstates.net/page=dispatch/id=2628328). 

# Requirements
- [uv](https://docs.astral.sh/uv/)
- [MySQL Community Server](https://dev.mysql.com/downloads/mysql/)

# Installation
- ``git clone https://github.com/Europeia/recruitment-tool.git``
- ``cd recruitment-tool``
- ``mkdir logs``
- ``cp settings.json.default settings.json``
- ``nano settings.json``
    - customize using your values

# Execution
- ``uv run main.py``
