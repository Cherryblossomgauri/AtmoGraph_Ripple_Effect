
from functools import lru_cache

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from NLP.entity_resolver import EntityResolver

router = APIRouter(tags=["NLP"])


class AnalyzeRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        description="News article or disruption text"
    )


@lru_cache(maxsize=1)
def get_resolver():
    """Load the NLP pipeline once and reuse it."""
    return EntityResolver()


import traceback

@router.post("/analyze")
def analyze_news(request: AnalyzeRequest):
    try:
        resolver = get_resolver()
        return resolver.analyze(request.text)

    except Exception as error:
        print("\n========== NLP ERROR ==========")
        traceback.print_exc()
        print("================================\n")

        raise HTTPException(
            status_code=500,
            detail=f"NLP analysis failed: {str(error)}"
        ) from error