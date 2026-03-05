from typing import List, Optional

from openai.types import CompletionUsage
from pydantic import BaseModel
from nexus.lib.clients.openai import openai_client
from nexus.lib.costs.tokens import calculate_token_costs, token_costs_to_dataframe
from nexus.lib.scrapers.base import get_filename_from_url, scrape_website


class HomeDetails(BaseModel):
    address: str
    city: str
    state: str
    zip_code: str
    price: str
    bedrooms: float
    bathrooms: float
    square_footage: int
    lot_size: str
    year_built: int
    home_type: str
    days_on_market: int
    description: str
    amenities: list[str]
    school_rating: str
    neighborhood: str
    monthly_payment_estimate: str
    property_tax: str
    hoa_fee: Optional[str] = None
    fees: Optional[List[str]] = None


class HomeDetailsResponse(BaseModel):
    text: str
    details: HomeDetails
    usage: CompletionUsage | None


def get_home_details_from_zillow(url: str) -> HomeDetailsResponse:
    """Extract home details from a Zillow listing URL"""
    text = scrape_website(url)

    completion = openai_client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "Return details of the home listing with as many of these fields as you can find and determine based on the provided text and schema.",
            },
            {"role": "user", "content": text},
        ],
        response_format=HomeDetails,
    )

    response = completion.choices[0].message.parsed
    if not response:
        raise ValueError("Could not parse home details")

    return HomeDetailsResponse(text=text, details=response, usage=completion.usage)


def scrape_zillow(url: str) -> tuple[HomeDetailsResponse, str, str]:
    # Get home details using the extracted scraper function
    result = get_home_details_from_zillow(url)

    # Calculate costs using the extracted cost calculator
    cost_info = calculate_token_costs(result.usage)

    # Print cost information as a formatted table
    cost_table = token_costs_to_dataframe(cost_info)
    print(cost_table)

    # Save results to files
    url_filename = get_filename_from_url(url)
    filename = f"{url_filename}.json"
    markdown_filename = f"{url_filename}.md"

    return result, filename, markdown_filename
