from fastapi import APIRouter
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from ..schemas import Prompt, Response
from core.config import Settings

router = APIRouter(prefix="/llm", tags=["llm"])

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.0,
    api_key=Settings().openai_api_key,
)


@router.post("/guess", response_model=Response)
async def chat(body: Prompt) -> Response:
    """Uses a LLM to guess the licenses of the packages mentioned in the prompt.

    Keyword arguments:
    body -- the prompt to the LLM
    """
    msg = llm.invoke([
        (
            "system",
            "You are a helpful assistant that guesses the licenses for software packages. Make an educated guess on the packages given by the user. Politely refuse if the prompt does not feature known software."
        ),
        (
            "human",
            body.text
        )
    ])

    return Response(text=str(msg.content))
