import discord
import json

from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
from datetime import datetime, timedelta, timezone
from typing import Self, List

from components.errors import NotRegistered


@dataclass
class User:
    id: int
    nation: str
    template: str
    welcome_template: str | None
    active_session: bool = False
    allow_recruitment_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def set_next_recruitment(self, num_nations: int):
        self.allow_recruitment_at = datetime.now(timezone.utc) + timedelta(seconds=num_nations * 5)


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

    def get(self, user: discord.User) -> User:
        for recruiter in self.users:
            if recruiter.id == user.id:
                return recruiter
        raise NotRegistered(user)

    def ids(self) -> List[int]:
        return [user.id for user in self.users]

    def save(self):
        with open("config.json", "w") as out_file:
            out_file.write(self.to_json(indent=2))
