"""
CRM Integration for ag3ntwerk.

Provides integration with Salesforce and HubSpot.

Requirements:
    - Salesforce: pip install simple-salesforce
    - HubSpot: pip install hubspot-api-client

CRM is ideal for:
    - Customer data management
    - Sales pipeline tracking
    - Lead management
    - Revenue forecasting
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class CRMProvider(str, Enum):
    """CRM providers."""

    SALESFORCE = "salesforce"
    HUBSPOT = "hubspot"


@dataclass
class Contact:
    """Represents a CRM contact."""

    id: str
    email: str
    first_name: str = ""
    last_name: str = ""
    phone: str = ""
    company: str = ""
    title: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Company:
    """Represents a CRM company."""

    id: str
    name: str
    domain: str = ""
    industry: str = ""
    employees: int = 0
    revenue: float = 0
    website: str = ""
    created_at: Optional[datetime] = None
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Deal:
    """Represents a CRM deal/opportunity."""

    id: str
    name: str
    amount: float = 0
    stage: str = ""
    probability: float = 0
    close_date: Optional[datetime] = None
    contact_id: str = ""
    company_id: str = ""
    owner: str = ""
    created_at: Optional[datetime] = None
    properties: Dict[str, Any] = field(default_factory=dict)


class CRMIntegration:
    """
    Integration with CRM systems.

    Supports Salesforce and HubSpot.

    Example:
        # HubSpot
        crm = CRMIntegration(
            provider=CRMProvider.HUBSPOT,
            api_key="...",
        )

        # Get contacts
        contacts = await crm.list_contacts()

        # Create a deal
        deal = await crm.create_deal(Deal(
            name="Enterprise Contract",
            amount=50000,
            stage="proposal",
        ))
    """

    def __init__(
        self,
        provider: CRMProvider,
        api_key: str = "",
        username: str = "",
        password: str = "",
        security_token: str = "",  # Salesforce
        domain: str = "",  # Salesforce custom domain
    ):
        """Initialize CRM integration."""
        self.provider = provider
        self.api_key = api_key
        self.username = username
        self.password = password
        self.security_token = security_token
        self.domain = domain
        self._client = None

    def _get_salesforce(self):
        """Get Salesforce client."""
        if self._client is None:
            try:
                from simple_salesforce import Salesforce

                self._client = Salesforce(
                    username=self.username,
                    password=self.password,
                    security_token=self.security_token,
                    domain=self.domain or "login",
                )
            except ImportError:
                raise ImportError(
                    "simple-salesforce not installed. Install with: pip install simple-salesforce"
                )
        return self._client

    def _get_hubspot(self):
        """Get HubSpot client."""
        if self._client is None:
            try:
                from hubspot import HubSpot

                self._client = HubSpot(access_token=self.api_key)
            except ImportError:
                raise ImportError(
                    "hubspot-api-client not installed. Install with: pip install hubspot-api-client"
                )
        return self._client

    async def list_contacts(
        self,
        limit: int = 100,
        query: Optional[str] = None,
    ) -> List[Contact]:
        """
        List contacts.

        Args:
            limit: Maximum contacts
            query: Search query

        Returns:
            List of Contacts
        """
        if self.provider == CRMProvider.SALESFORCE:
            return await self._list_salesforce_contacts(limit, query)
        else:
            return await self._list_hubspot_contacts(limit, query)

    async def _list_salesforce_contacts(
        self,
        limit: int,
        query: Optional[str],
    ) -> List[Contact]:
        """List Salesforce contacts."""
        loop = asyncio.get_running_loop()
        sf = self._get_salesforce()

        def _list():
            # Sanitize inputs to prevent SOQL injection
            safe_limit = int(limit)
            soql = f"SELECT Id, Email, FirstName, LastName, Phone, Title, Account.Name FROM Contact LIMIT {safe_limit}"
            if query:
                safe_query = query.replace("'", "\\'").replace("\\", "\\\\")
                soql = f"SELECT Id, Email, FirstName, LastName, Phone, Title, Account.Name FROM Contact WHERE Name LIKE '%{safe_query}%' LIMIT {safe_limit}"

            result = sf.query(soql)
            return [
                Contact(
                    id=r["Id"],
                    email=r.get("Email", ""),
                    first_name=r.get("FirstName", ""),
                    last_name=r.get("LastName", ""),
                    phone=r.get("Phone", ""),
                    title=r.get("Title", ""),
                    company=r.get("Account", {}).get("Name", "") if r.get("Account") else "",
                )
                for r in result.get("records", [])
            ]

        return await loop.run_in_executor(None, _list)

    async def _list_hubspot_contacts(
        self,
        limit: int,
        query: Optional[str],
    ) -> List[Contact]:
        """List HubSpot contacts."""
        loop = asyncio.get_running_loop()
        hs = self._get_hubspot()

        def _list():
            if query:
                result = hs.crm.contacts.search_api.do_search(
                    public_object_search_request={
                        "query": query,
                        "limit": limit,
                    }
                )
            else:
                result = hs.crm.contacts.basic_api.get_page(
                    limit=limit,
                    properties=["email", "firstname", "lastname", "phone", "company"],
                )

            return [
                Contact(
                    id=r.id,
                    email=r.properties.get("email", ""),
                    first_name=r.properties.get("firstname", ""),
                    last_name=r.properties.get("lastname", ""),
                    phone=r.properties.get("phone", ""),
                    company=r.properties.get("company", ""),
                )
                for r in result.results
            ]

        return await loop.run_in_executor(None, _list)

    async def create_contact(self, contact: Contact) -> Contact:
        """Create a contact."""
        if self.provider == CRMProvider.SALESFORCE:
            return await self._create_salesforce_contact(contact)
        else:
            return await self._create_hubspot_contact(contact)

    async def _create_salesforce_contact(self, contact: Contact) -> Contact:
        """Create Salesforce contact."""
        loop = asyncio.get_running_loop()
        sf = self._get_salesforce()

        def _create():
            result = sf.Contact.create(
                {
                    "Email": contact.email,
                    "FirstName": contact.first_name,
                    "LastName": contact.last_name,
                    "Phone": contact.phone,
                    "Title": contact.title,
                }
            )
            contact.id = result["id"]
            return contact

        return await loop.run_in_executor(None, _create)

    async def _create_hubspot_contact(self, contact: Contact) -> Contact:
        """Create HubSpot contact."""
        loop = asyncio.get_running_loop()
        hs = self._get_hubspot()

        def _create():
            result = hs.crm.contacts.basic_api.create(
                simple_public_object_input_for_create={
                    "properties": {
                        "email": contact.email,
                        "firstname": contact.first_name,
                        "lastname": contact.last_name,
                        "phone": contact.phone,
                        "company": contact.company,
                    }
                }
            )
            contact.id = result.id
            return contact

        return await loop.run_in_executor(None, _create)

    async def list_deals(
        self,
        limit: int = 100,
        stage: Optional[str] = None,
    ) -> List[Deal]:
        """
        List deals/opportunities.

        Args:
            limit: Maximum deals
            stage: Filter by stage

        Returns:
            List of Deals
        """
        if self.provider == CRMProvider.SALESFORCE:
            return await self._list_salesforce_deals(limit, stage)
        else:
            return await self._list_hubspot_deals(limit, stage)

    async def _list_salesforce_deals(
        self,
        limit: int,
        stage: Optional[str],
    ) -> List[Deal]:
        """List Salesforce opportunities."""
        loop = asyncio.get_running_loop()
        sf = self._get_salesforce()

        def _list():
            # Sanitize inputs to prevent SOQL injection
            safe_limit = int(limit)
            soql = f"SELECT Id, Name, Amount, StageName, Probability, CloseDate FROM Opportunity LIMIT {safe_limit}"
            if stage:
                safe_stage = stage.replace("'", "\\'").replace("\\", "\\\\")
                soql = f"SELECT Id, Name, Amount, StageName, Probability, CloseDate FROM Opportunity WHERE StageName = '{safe_stage}' LIMIT {safe_limit}"

            result = sf.query(soql)
            return [
                Deal(
                    id=r["Id"],
                    name=r.get("Name", ""),
                    amount=r.get("Amount", 0) or 0,
                    stage=r.get("StageName", ""),
                    probability=r.get("Probability", 0) or 0,
                    close_date=(
                        datetime.fromisoformat(r["CloseDate"]) if r.get("CloseDate") else None
                    ),
                )
                for r in result.get("records", [])
            ]

        return await loop.run_in_executor(None, _list)

    async def _list_hubspot_deals(
        self,
        limit: int,
        stage: Optional[str],
    ) -> List[Deal]:
        """List HubSpot deals."""
        loop = asyncio.get_running_loop()
        hs = self._get_hubspot()

        def _list():
            result = hs.crm.deals.basic_api.get_page(
                limit=limit,
                properties=["dealname", "amount", "dealstage", "closedate"],
            )

            deals = []
            for r in result.results:
                if stage and r.properties.get("dealstage") != stage:
                    continue
                deals.append(
                    Deal(
                        id=r.id,
                        name=r.properties.get("dealname", ""),
                        amount=float(r.properties.get("amount", 0) or 0),
                        stage=r.properties.get("dealstage", ""),
                    )
                )

            return deals

        return await loop.run_in_executor(None, _list)

    async def create_deal(self, deal: Deal) -> Deal:
        """Create a deal/opportunity."""
        if self.provider == CRMProvider.SALESFORCE:
            return await self._create_salesforce_deal(deal)
        else:
            return await self._create_hubspot_deal(deal)

    async def _create_salesforce_deal(self, deal: Deal) -> Deal:
        """Create Salesforce opportunity."""
        loop = asyncio.get_running_loop()
        sf = self._get_salesforce()

        def _create():
            data = {
                "Name": deal.name,
                "Amount": deal.amount,
                "StageName": deal.stage,
            }
            if deal.close_date:
                data["CloseDate"] = deal.close_date.strftime("%Y-%m-%d")

            result = sf.Opportunity.create(data)
            deal.id = result["id"]
            return deal

        return await loop.run_in_executor(None, _create)

    async def _create_hubspot_deal(self, deal: Deal) -> Deal:
        """Create HubSpot deal."""
        loop = asyncio.get_running_loop()
        hs = self._get_hubspot()

        def _create():
            result = hs.crm.deals.basic_api.create(
                simple_public_object_input_for_create={
                    "properties": {
                        "dealname": deal.name,
                        "amount": str(deal.amount),
                        "dealstage": deal.stage,
                    }
                }
            )
            deal.id = result.id
            return deal

        return await loop.run_in_executor(None, _create)

    async def get_pipeline_summary(self) -> Dict[str, Any]:
        """
        Get sales pipeline summary.

        Returns:
            Dict with pipeline metrics
        """
        deals = await self.list_deals(limit=1000)

        stages = {}
        total_value = 0
        weighted_value = 0

        for deal in deals:
            stage = deal.stage or "Unknown"
            if stage not in stages:
                stages[stage] = {"count": 0, "value": 0}

            stages[stage]["count"] += 1
            stages[stage]["value"] += deal.amount
            total_value += deal.amount
            weighted_value += deal.amount * (deal.probability / 100)

        return {
            "total_deals": len(deals),
            "total_value": total_value,
            "weighted_value": weighted_value,
            "stages": stages,
        }
