from fastapi import APIRouter
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from ..schemas import LlmPrompt, LlmResponse
from core.config import Settings

router = APIRouter(prefix="/llm", tags=["llm"])

settings = Settings()
if not settings.openai_api_key:
    raise RuntimeError("OPENAI_API_KEY is required to call the LLM.")

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.0,
    api_key=settings.openai_api_key,
)


@router.post("/guess", response_model=LlmResponse, deprecated=True)
async def chat(body: LlmPrompt) -> LlmResponse:
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

    return LlmResponse(text=str(msg.content))
