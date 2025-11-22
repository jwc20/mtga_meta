from contextlib import asynccontextmanager
from typing import Annotated, Literal, Optional

from fastapi.middleware.cors import CORSMiddleware

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from sqlmodel import Field, Session, SQLModel, create_engine, select

import uuid
from pathlib import Path
from datetime import datetime


##############################################################################


def find_project_root(marker=".git"):
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / marker).exists():
            return parent
    return current.parent


project_root = find_project_root()
db_path = project_root / "database.db"


class ChatMessage(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(index=True)
    timestamp: datetime = Field(index=True)
    channel_name: str = Field(index=True)
    username: str | None = Field(default=None, index=True)
    message_text: str
    message_type: str = Field(index=True)


##############################################################################


sqlite_url = f"sqlite:///{db_path}"
connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, echo=True, connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


##############################################################################

def add_cors_middleware(fastapi_app):
    return CORSMiddleware(
        app=fastapi_app,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    create_db_and_tables()
    yield
    print("shutting down")


app = FastAPI(lifespan=lifespan)
# noinspection PyTypeChecker
app.add_middleware(add_cors_middleware)


@app.middleware("http")
async def add_logging_middleware(request: Request, call_next):
    print(f"Request path: {request.url.path}")
    response: Response = await call_next(request)
    print(f"Response status: {response.status_code}")
    return response


##############################################################################


@app.get("/")
def root(request):
    return {"Hello": "World"}

@app.get("/chats/", response_model=list[ChatMessage])
async def read_chats(
        session: SessionDep,
        channel_name: Annotated[str | None, Query()] = None,
        username: Annotated[str | None, Query()] = None,
        message_type: Annotated[str | None, Query()] = None,
        start_datetime: Optional[datetime] = Query(None),
        end_datetime: Optional[datetime] = Query(None),
        offset: int = 0,
        limit: Annotated[int, Query(ge=1, le=100)] = 100,
        order_by: Annotated[
            Literal["timestamp", "username", "message_type"], Query()
        ] = "timestamp",
        desc: bool = False,
) -> list[ChatMessage]:
    stmt = select(ChatMessage)

    if channel_name is not None:
        stmt = stmt.where(getattr(ChatMessage, "channel_name") == channel_name)

    if username is not None:
        stmt = stmt.where(getattr(ChatMessage, "username") == username)

    if message_type is not None:
        stmt = stmt.where(getattr(ChatMessage, "message_type") == message_type)

    if start_datetime is not None:
        stmt = stmt.where(getattr(ChatMessage, "timestamp") >= start_datetime)

    if end_datetime is not None:
        stmt = stmt.where(getattr(ChatMessage, "timestamp") <= end_datetime)

    if desc:
        stmt = stmt.order_by(getattr(ChatMessage, order_by).desc())
    else:
        stmt = stmt.order_by(getattr(ChatMessage, order_by))

    stmt = stmt.offset(offset).limit(limit)

    results = session.exec(stmt).all()
    return list(results)
