"""
Company Database API Client.

HTTP client for querying the external company database API.
"""

import os
import json
import requests
from typing import Dict, Any, Optional
from dataclasses import dataclass


# Configuration from environment
COMPANY_API_URL = os.getenv("COMPANY_API_URL", "http://185.246.84.224:5001")
COMPANY_API_KEY = os.getenv("COMPANY_API_KEY", "")
API_TIMEOUT = int(os.getenv("COMPANY_API_TIMEOUT", "60"))


@dataclass
class APIResponse:
    """Response from the company database API."""
    success: bool
    count: int
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class CompanyAPIError(Exception):
    """Exception raised when API call fails."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class CompanyAPIClient:
    """
    Client for the company database API.

    Handles HTTP communication with the external company count API.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = API_TIMEOUT
    ):
        """
        Initialize the API client.

        Args:
            base_url: API base URL (defaults to env COMPANY_API_URL)
            api_key: API key (defaults to env COMPANY_API_KEY)
            timeout: Request timeout in seconds
        """
        self.base_url = (base_url or COMPANY_API_URL).rstrip('/')
        self.api_key = api_key or COMPANY_API_KEY
        self.timeout = timeout

        if not self.api_key:
            print("[CompanyAPIClient] WARNING: No API key configured. Set COMPANY_API_KEY environment variable.")

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def count_companies(self, criteria: Dict[str, Any]) -> APIResponse:
        """
        Query the API for company count matching criteria.

        Args:
            criteria: Search criteria in API format:
                {
                    "location": {"present": bool, "city": [], "region": [], ...},
                    "activity": {"present": bool, "activity_codes_list": [], "original_activity_request": str},
                    "company_size": {"present": bool, "employees_number_range": []},
                    "financial_criteria": {"present": bool, ...},
                    "legal_criteria": {"present": bool, "headquarters": bool}
                }

        Returns:
            APIResponse with count and data

        Raises:
            CompanyAPIError: If the API call fails
        """
        endpoint = f"{self.base_url}/count_bot_v1"

        try:
            response = requests.post(
                endpoint,
                headers=self._get_headers(),
                json=criteria,
                timeout=self.timeout,
            )

            # Handle response codes
            if response.status_code == 200:
                data = response.json()
                # API returns count_legal as the main count
                count = data.get("count_legal", data.get("count", 0))
                return APIResponse(
                    success=True,
                    count=count,
                    data=data,
                )

            elif response.status_code == 401:
                raise CompanyAPIError(
                    "Unauthorized: Invalid or missing API key",
                    status_code=401
                )

            elif response.status_code == 400:
                error_data = response.json() if response.text else {}
                raise CompanyAPIError(
                    f"Bad request: {error_data.get('error', 'Invalid JSON')}",
                    status_code=400
                )

            elif response.status_code == 456:
                raise CompanyAPIError(
                    "Criteria mismatch: The provided criteria are incompatible",
                    status_code=456
                )

            else:
                raise CompanyAPIError(
                    f"API error: {response.status_code} - {response.text[:200]}",
                    status_code=response.status_code
                )

        except requests.exceptions.Timeout:
            raise CompanyAPIError(
                f"Request timeout after {self.timeout} seconds",
                status_code=None
            )

        except requests.exceptions.ConnectionError as e:
            raise CompanyAPIError(
                f"Connection error: Unable to reach API at {self.base_url}",
                status_code=None
            )

        except requests.exceptions.RequestException as e:
            raise CompanyAPIError(
                f"Request failed: {str(e)}",
                status_code=None
            )

    def health_check(self) -> bool:
        """
        Check if the API is reachable.

        Returns:
            True if API is responding, False otherwise
        """
        try:
            response = requests.get(
                self.base_url,
                headers=self._get_headers(),
                timeout=5,
            )
            return response.status_code < 500
        except Exception:
            return False


# Module-level singleton
_client: Optional[CompanyAPIClient] = None


def get_company_api_client() -> CompanyAPIClient:
    """Get or create the singleton CompanyAPIClient instance."""
    global _client
    if _client is None:
        _client = CompanyAPIClient()
    return _client


# Convenience function
def count_companies(criteria: Dict[str, Any]) -> APIResponse:
    """
    Convenience function to count companies matching criteria.

    Args:
        criteria: Search criteria in API format

    Returns:
        APIResponse with count and data
    """
    return get_company_api_client().count_companies(criteria)
