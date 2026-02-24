from fastapi import APIRouter, HTTPException, Query
from snakesss.lib.scrapers import scrape_website
from snakesss.cli.crawlers.job_post import convert_text_to_job_post  # existing conversion logic
from snakesss.lib.scrapers.zillow_scraper import scrape_zillow  # existing Zillow scraper logic

router = APIRouter(prefix="/scrape")


@router.get("/scrape")
async def scrape(url: str = Query(..., description="URL to scrape")):
    try:
        text = scrape_website(url)
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))
    return {"url": url, "text": text}


@router.get("/job-post")
async def scrape_job_post(url: str = Query(..., description="URL to scrape for a job post")):
    try:
        text = scrape_website(url)
        if not text:
            raise HTTPException(status_code=404, detail="No text found on the website")
        response = convert_text_to_job_post(text)
        response.url = url
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))
    return response.model_dump()  # return JSON-compatible dict


@router.get("/zillow")
async def scrape_zillow_route(url: str = Query(..., description="URL to scrape for Zillow details")):
    try:
        result, _, _ = scrape_zillow(url)
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))
    return result.model_dump()  # return JSON-compatible dict
