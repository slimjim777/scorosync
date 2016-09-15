import requests
import logging
from xml.dom.minidom import parse
from xml.dom.minidom import parseString


logger = logging.getLogger("clearbooks")


class ClearBooks(object):
    """
    Interact with the ClearBooks API.
    """
    URL = "https://secure.clearbooks.co.uk/api/soap/"
    URI = "https://secure.clearbooks.co.uk/api/accounting/soap/"
    HEADERS = {
        "Content-Type": "text/xml",
    }

    REQUEST = """<?xml version="1.0" encoding="UTF-8"?>
        <SOAP-ENV:Envelope 
            xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:ns1="https://secure.clearbooks.co.uk/api/accounting/soap/" 
            xmlns:xsd="http://www.w3.org/2001/XMLSchema">
        <SOAP-ENV:Header>
            <ns1:authenticate>
            <apiKey>{api_key}</apiKey>
            </ns1:authenticate>
        </SOAP-ENV:Header>
        <SOAP-ENV:Body>
            {body}
        </SOAP-ENV:Body>
        </SOAP-ENV:Envelope>
    """

    def __init__(self, api_key):
        self.api_key = api_key

    def _post(self, body, action):
        payload = self.REQUEST.format(**{"api_key": self.api_key, "body": body})
        headers = self.HEADERS.copy()
        headers["SOAPAction"] = self.URI + "#" + action

        response = requests.post(self.URL, data=payload, headers=headers)

        dom = parseString(response.text)
        return dom

    def create_customer(self, customer):
        """
        Create customer.
        """
        body = """
            <ns1:createEntity>
            <entity
                company_name="{company_name}"
                building="{building}"
                address1="{address1}"
                address2="{address2}"
                town="{town}"
                county="{county}"
                country="{country}"
                postcode="{postcode}"
                email="{email}"
                phone1="{phone1}"
                phone2="{phone2}"
                fax="{fax}"
                website="{website}"
                external_id="{external_id}">
                <customer default_account_code="0" default_vat_rate="0.00" default_credit_terms="30" />
            </entity>
            </ns1:createEntity>
        """.format(**customer)

        payload = self.REQUEST.format(**{"api_key": self.api_key, "body": body})
        headers = self.HEADERS.copy()
        headers["SOAPAction"] = self.URI + "#createEntity"

        response = requests.post(self.URL, data=payload, headers=self.HEADERS)

        dom = parseString(response.text)
        el = dom.getElementsByTagName("createEntityReturn")[0]
        return el.nodeValue

    def _invoice_items(self, items):
        body = """
        <ns1:Item
            vatRate="{vatRate}"
            project="0"
            type="{type}"
            quantity="{quantity}"
            unitPrice="{unitPrice}">
                <description>{description}</description>
        </ns1:Item>
        """
        xml = ""
        for i in items:
            xml += body.format(**i)
        return xml

    def create_invoice(self, invoice):
        """
        Create invoice.
        """
        invoice["item_body"] = self._invoice_items(invoice["items"])
        body = """
            <ns1:createInvoice>
            <invoice
                invoice_prefix="INV"
                invoice_number="{invoice_number}"
                entityId="{entityId}"
                dateDue="{dateDue}"
                dateCreated="{dateCreated}"
                type="sales"
                creditTerms="30"
                project="0"
                status="approved">
                <items>
                    {item_body}
                </items>
                <description>{description}</description>
                <reference>{reference}</reference>
                <type>sales</type>
            </invoice>
            </ns1:createInvoice>
        """.format(**invoice)

        payload = self.REQUEST.format(**{"api_key": self.api_key, "body": body})
        headers = self.HEADERS.copy()
        headers["SOAPAction"] = self.URI + "#createInvoice"

        response = requests.post(self.URL, data=payload, headers=self.HEADERS)

        dom = parseString(response.text)
        #print( dom.toprettyxml() )
        el = dom.getElementsByTagName("createInvoiceReturn")[0]

        inv = {
            "invoice_id": el.getAttribute("invoice_id"),
            "invoice_prefix": el.getAttribute("invoice_prefix"),
            "invoice_number": el.getAttribute("invoice_number"),
        }
        return inv

    def list_invoices(self, fromDate):
        body = """
            <ns1:listInvoices>
            <query ledger="sales">
            </query>
            </ns1:listInvoices>
        """

        payload = self.REQUEST.format(**{"api_key": self.api_key, "body": body})
        headers = self.HEADERS.copy()
        headers["SOAPAction"] = self.URI + "#listInvoices"

        response = requests.post(self.URL, data=payload, headers=headers)

        dom = parseString(response.text)
        elements = dom.getElementsByTagName("ns1:Invoice")

        invoices = []
        for el in elements:
            invoices.append({
                "entity_id": el.getAttribute("entityId"),
                "invoice_id": el.getAttribute("invoice_id"),
                "invoice_prefix": el.getAttribute("invoice_prefix"),
                "invoice_number": el.getAttribute("invoiceNumber"),
                "date_created": el.getAttribute("dateCreated"),
                "reference": el.getAttribute("reference"),
                "status": el.getAttribute("status"),
                "gross": el.getAttribute("gross"),
                "net": el.getAttribute("net"),
                "vat": el.getAttribute("vat"),
            })

        return invoices

    def list_customers(self):
        """
        Fetch all the customers.
        """
        body = """
            <ns1:listEntities>
            <query type="customer">
            </query>
            </ns1:listEntities>
        """

        payload = self.REQUEST.format(**{"api_key": self.api_key, "body": body})
        headers = self.HEADERS.copy()
        headers["SOAPAction"] = self.URI + "#listEntities"

        response = requests.post(self.URL, data=payload, headers=headers)

        dom = parseString(response.text)
        records = dom.getElementsByTagName("ns1:Entity")

        customers = {}
        for el in records:
            customers[el.getAttribute("company_name")] = el.getAttribute("id")
        return customers

    def list_account_codes(self):
        """
        Fetch all the account codes.
        """
        body = """
            <ns1:listAccountCodes>
            </ns1:listAccountCodes>
        """
        dom = self._post(body, "listAccountCodes")
        records = dom.getElementsByTagName("ns1:AccountCode")

        accounts = {}
        for el in records:
            account_name = el.getAttribute("account_name").replace("&amp;", "&")
            accounts[account_name] = el.getAttribute("id")
        return accounts
