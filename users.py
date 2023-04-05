import json

from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
from typing import Self


@dataclass
class User:
    id: int
    nation: str
    template: str


@dataclass_json
@dataclass
class Users:
    users: list[User] = field(default_factory=list)

    def from_file(self) -> Self:
        try:
            with open("config.json", "r") as in_file:
                data = json.load(in_file)
        except:
            users = Users()
        else:
            users = self.from_dict(data)
        finally:
            return users

    def add(self, user: User):
        # prevents duplicate users
        self.users = [
            current_user for current_user in self.users if current_user.id != user.id]

        self.users.append(user)

        self.save()

    def get(self, id: int):
        for user in self.users:
            if user.id == id:
                return user
        return None

    def save(self):
        with open("config.json", "w") as out_file:
            out_file.write(self.to_json(indent=2))
