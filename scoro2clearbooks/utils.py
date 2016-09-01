import sys
import configparser
import logging
from scoro2clearbooks.scoro import Scoro
from scoro2clearbooks.clearbooks import ClearBooks

logger = logging.getLogger("utils")



def run_sync():
    # Get the config file and parse it
    logger.info("Read config file")
    config = _read_config()

    # Fetch the customers and invoices from ClearBooks
    clearbooks = ClearBooks(config["clearbooks"]["api_key"])
    clearbooks_customers = clearbooks.list_customers()
    clearbooks_accounts = clearbooks.list_account_codes()
    print("CB_CUST________________________", clearbooks_customers)

    # Cache the accounting objects from Scoro
    c = config["scoro"]
    scoro = Scoro(c["base_url"], c["company_account_id"], c["api_key"])    
    scoro.accounting_objects()

    # Fetch the unpaid invoices from Scoro
    invoices = scoro.invoices()

    # Process each of the Scoro invoices
    for inv in invoices:
        if inv["no"] != "4489":
            continue

        # Get the full invoice details
        invoice = scoro.invoice(inv["id"])
        print("\n***\n", invoice)
        
        # Fetch the customer from Scoro
        customer = scoro.contact(invoice["company_id"])
        print("CUSTOMER\n", customer)

        # Check if the customer is already on Clearbooks
        cust_name = customer["name"].replace("&amp;", "&")
        if clearbooks_customers.get(cust_name):
            cb_cust_id = clearbooks_customers.get(cust_name)
        else:
            # Create the customer in ClearBooks
            cb_customer = scoro.clearbooks_customer(customer)
            cb_cust_id = clearbooks.create_customer(cb_customer)
        print("CB_CUSTOMER", cb_cust_id)

        # Get the invoice project
        if invoice.get("project_id"):
            project = scoro.project(invoice.get("project_id"))
            invoice["project_name"] = project.get("description", "")
        else:
            invoice["project_name"] = ""

        # Map fields and create the invoice in ClearBooks
        cb_invoice = scoro.clearbooks_invoice(cb_cust_id, invoice, clearbooks_accounts)
        print("\nCB INVOICE\n", cb_invoice)
        #clearbooks.create_invoice(cb_invoice)


def _read_config():
    cfg = configparser.ConfigParser()
    cfg.read("settings.ini")

    options = {"scoro": {}, "clearbooks": {}}

    # Get the Scoro options
    options_scoro = cfg.options("scoro")
    for o in options_scoro:
        options["scoro"][o] = cfg.get("scoro", o)

    # Get the ClearBooks options
    options_scoro = cfg.options("clearbooks")
    for o in options_scoro:
        options["clearbooks"][o] = cfg.get("clearbooks", o)

    return options
