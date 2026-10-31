from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session


def database_session(request: Request) -> Iterator[Session]:
    # Mutating routes commit explicitly before constructing a success response.
    # On every failure, close() rolls back the entire uncommitted transaction.
    with Session(request.app.state.database.engine, expire_on_commit=False) as session:
        yield session


DB = Annotated[Session, Depends(database_session)]
