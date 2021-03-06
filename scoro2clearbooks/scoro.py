# -*- coding: utf-8 -*-
import requests
import json
import logging
import pycountry
import html
from urllib.parse import urlencode


logger = logging.getLogger("scoro")


FROM_DATE = "2016-09-01"


class Scoro(object):
    """
    Interact with the Scoro API.
    """
    PER_PAGE = 40
    products = {}
    product_groups = {}
    finance_objects = {}

    def __init__(self, base_url, company_account_id, api_key, lang="eng"):
        self.base_url = base_url
        self.auth = {
            "company_account_id": company_account_id,
            "apiKey": api_key,
            "lang": lang,
            "per_page": self.PER_PAGE,
        }

    def _url(self, method, action=None, record_id=None):
        url = self.base_url + method
        if action:
            url += "/" + action
        if record_id:
            url += "/" + str(record_id)
        return url

    def fetch(self, method, action=None, record_id=None, options=None):
        url = self._url(method, action=action, record_id=record_id)
        payload = self.auth.copy()
        if options:
            payload.update(options)

        response = requests.post(url, data=json.dumps(payload))
        results = response.json()
        return self.check_error(results)

    def check_error(self, results):
        if results["status"] == "OK":
            return True, results.get("data")
        else:
            logger.error(results)
            return False, results.get("message")

    def invoices(self):
        """
        Fetch the invoices that need to be transferred to the accounts system.
        """
        logger.info("Fetch unpaid invoices")
        options = {
            "filter": {
                "custom_fields": {"c_clearbooksref": ""},
                "date": {"from": FROM_DATE},
            }
        }
        status, records = self.fetch("invoices", options=options)
        logger.info("Found {0} invoices".format(len(records)))
        return records

    def invoice(self, record_id):
        """
        Fetch a specific invoice, which will include the lines.
        """
        return self.fetch("invoices", action="view", record_id=record_id)[1]

    def contact(self, record_id):
        """
        Fetch a single customer or contact record.
        """
        return self.fetch("contacts", action="view", record_id=record_id)[1]

    def project(self, record_id):
        """
        Fetch a single project record.
        """
        return self.fetch("projects", action="view", record_id=record_id)[1]

    def product(self, record_id):
        """
        Fetch a single product record.
        """
        if record_id in self.products:
            return self.products[record_id]
        else:
            p = self.fetch("products", action="view", record_id=record_id)[1]
            self.products[record_id] = {"name": p["name"]}

            # Get the product group
            if p.get("productgroup_id") and p.get("productgroup_id") != "0":
                grp = self.product_group(p["productgroup_id"])
                self.products[record_id]["group"] = grp
            return self.products[record_id]

    def product_group(self, record_id):
        """
        Fetch a single product group record.
        """
        if record_id in self.product_groups:
            return self.product_groups[record_id]
        else:
            p = self.fetch("productGroups", action="view", record_id=record_id)[1]
            self.product_groups[record_id] = p["name"]
            return self.product_groups[record_id]

    def accounting_object(self, record_id):
        """
        Fetch a single accounting object record.
        """
        if record_id in self.finance_objects:
            return self.finance_objects[record_id]
        else:
            p = self.fetch("financeObjects", action="view", record_id=record_id)[1]
            self.finance_objects[record_id] = p["name"]
            return self.finance_objects[record_id]

    def accounting_objects(self):
        """
        Fetch all the accounting objects.
        """
        response, accts = self.fetch("financeObjects", action="list")
        if not response:
            return {}

        for a in accts:
            if a["name"]:
                self.finance_objects[a["object_id"]] = a["name"].replace("&amp;", "&")
            else:
                self.finance_objects[a["object_id"]] = ""
        return self.finance_objects

    def clearbooks_customer(self, c):
        """
        Converts a Scoro customer record to a ClearBooks customer.
        """
        if c.get("contact_type") == "person":
            company = "{0} {1}".format(c.get("name"), c.get("lastname"))
            contact_name = company
        else:
            company = c.get("name")
            contact_name = ""

        if len(c.get("addresses", [])) == 0:
            a = {}
            building = ""
            country = ""
            address1 = ""
            address2 = ""
            county = ""
        else:
            a = c["addresses"][0]

            # Split the address street
            lines = a.get("street", "").split("\r\n")
            building = ""
            address1 = lines[0]
            if len(lines) > 1:
                address2 = " ".join(lines[1:])
            else:
                address2 = ""
            if len(lines) > 2:
                building = lines[0]
                address1 = lines[1]
                address2 = " ".join(lines[2:])

            # Country codes need to be a two-character format
            if a.get("country") and len(a.get("country")) > 0:
                if a["country"] == "United Kingdom":
                    a["country"] = "GBR"
                country = pycountry.countries.get(alpha3=a.get("country").upper()).alpha2
            else:
                country = ""

        # Contact details
        contact = c.get("means_of_contact", {})
        if not contact:
            contact = {}
        if isinstance(contact, list):
            contact = {}
        emails = contact.get("email", [])
        email = emails[0] if len(emails) > 0 else ""
        phones = contact.get("phone", [])
        phone1 = phones[0] if len(phones) > 0 else ""
        phone2 = phones[1] if len(phones) > 1 else ""
        faxes = contact.get("fax", [])
        fax = faxes[0] if len(faxes) > 0 else ""
        websites = contact.get("website", [])
        website = websites[0] if len(websites) > 0 else ""

        return {
            "company_name": self.clean_text(company),
            "contact_name": self.clean_text(contact_name),
            "building": self.clean_text(building),
            "address1": self.clean_text(address1),
            "address2": self.clean_text(address2),
            "town": a.get("city"),
            "county": a.get("county"),
            "country": country,
            "postcode": a.get("zipcode"),
            "email": email,
            "phone1": phone1,
            "phone2": phone2,
            "fax": fax,
            "website": website,
            "external_id": a.get("contact_id"),
        }

    def clean_text(self, s):
        return s.encode("latin-1", "ignore").decode("latin-1").replace("£", "GBP")

    def clearbooks_discount(self, percent, amount):
        return {
            "unitPrice": amount,
            "quantity": 1.0,
            "description": "Discount {}%".format(percent),
            "type": "3001001",
            "vatRate": 0.0,
        }

    def clearbooks_invoice(self, customer_id, i, clearbooks_accounts):
        """
        Converts a Scoro invoice record to a ClearBooks invoice.
        """
        items = []
        amount = 0.0

        if not i.get("lines"):
            return {
                "invoice_number": i.get("no"),
                "entityId": customer_id,
                "dateCreated": i.get("date"),
                "dateDue": i.get("deadline"),
                "description": urlencode(self.clean_text(i.get("description", ""))),
                "creditTerms": "30",
                "reference": html.escape(self.clean_text(i.get("project_code", ""))[:255]),
                "type": "sales",
                "items": items,
            }

        for l in i.get("lines", []):
            #print(l)
            # Ignore invalid group lines with no value
            if int(l["product_id"]) == -1 and l["amount"] == '0.000000':
                continue

            # Get the product and create the description
            prod = self.product(l["product_id"])
            d = "{0}\n{1}".format(prod["name"], l.get("comment", ""))

            # Convert the finance object ID to a name
            if l["finance_object_id"] == 0:
                logger.info(
                    "Error: the Accounting Object is not set: %s: %s",
                    i.get("no"),
                    l.get("comment", ""))
            acct_name = self.accounting_object(l["finance_object_id"])

            # Look up the account code from the ClearBooks dictionary
            # Default: Other Income = 3001001
            print(acct_name)
            cb_acct_id = clearbooks_accounts.get(acct_name, "3001001")


            items.append({
                "unitPrice": l["price"],
                "quantity": l["amount"],
                "description": self.clean_text(prod["name"]),
                "type": cb_acct_id,
                "vatRate": float(l["vat"]) / 100.0,
            })
            amount += float(l.get("sum", 0.0))

            if float(i.get("discount", 0.0)) > 0.0:
                item = self.clearbooks_discount(i.get("discount"), float(i.get("sum", 0.0)) - amount)
                items.append(item)

        return {
            "invoice_number": i.get("no"),
            "entityId": customer_id,
            "dateCreated": i.get("date"),
            "dateDue": i.get("deadline"),
            "description": self.clean_text(i.get("description", "")),
            "creditTerms": "30",
            "reference": html.escape(self.clean_text(i.get("project_code", ""))[:255]),
            "type": "sales",
            "items": items,
        }

    def update_invoice(self, invoice, cb_inv_no):
        """
        Update the custom field on the invoice with the number from ClearBooks.
        """
        # Remove the finance_account_id as finance accounts is unused
        if invoice["lines"]:
            lines = []
            for l in invoice["lines"]:
                if "finance_account_id" in l:
                    del l["finance_account_id"]
                lines.append(l)
            invoice["lines"] = lines

        invoice["custom_fields"]["c_clearbooksref"] = cb_inv_no
        options = {
            "request": invoice
        }

        return self.fetch(
            "invoices", action="modify", record_id=invoice["id"], options=options)
