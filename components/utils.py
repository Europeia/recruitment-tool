class Utils:
    @classmethod
    def TryParseInt(cls, value: str) -> tuple[bool, int]:
        try:
            return True, int(value)
        except (ValueError, TypeError):
            return False, 0
