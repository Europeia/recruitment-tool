from models.nation import Nation
from datetime import datetime, timedelta


class Filter:
    def __init__(self):
        self._seen: list[Nation] = []

    def _purge(self):
        self._seen = [nation for nation in self._seen if nation.founding_time > datetime.now() - timedelta(minutes=90)]

    def filter(self, nation: Nation) -> Nation | None:
        self._purge()

        if nation in self._seen:
            return None

        self._seen.append(nation)

        return nation
