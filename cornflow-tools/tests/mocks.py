class MockColumn:
    def __init__(
        self,
        type_col,
        foreign_key=None,
        nullable=None,
        primary_key=None,
        autoincrement=None,
    ):
        self.type_col = type_col
        self.foreign_key = foreign_key
        self.nullable = nullable
        self.primary_key = primary_key
        self.autoincrement = autoincrement
