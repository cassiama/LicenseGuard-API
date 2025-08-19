from pydantic import BaseModel


class Prompt(BaseModel):
    text: str


class Response(BaseModel):
    text: str
