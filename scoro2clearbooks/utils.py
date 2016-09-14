import sys
import os
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

    # Cache the accounting objects from Scoro
    c = config["scoro"]
    scoro = Scoro(c["base_url"], c["company_account_id"], c["api_key"])    
    scoro.accounting_objects()

    # Fetch the unpaid invoices from Scoro
    invoices = scoro.invoices()
    # for inv in invoices:
    #     print(inv["no"])
    # return

    # Process each of the Scoro invoices
    errors = []
    for inv in invoices:
        try:
            # if inv["no"] != "4508":
            #     continue

            logger.info("Process invoice {}".format(inv["no"]))

            # Get the full invoice details
            invoice = scoro.invoice(inv["id"])

            # Fetch the customer from Scoro
            customer = scoro.contact(invoice["company_id"])

            # Check if the customer is already on Clearbooks
            cust_name = customer["name"].replace("&amp;", "&")
            if clearbooks_customers.get(cust_name):
                cb_cust_id = clearbooks_customers.get(cust_name)
            else:
                # Create the customer in ClearBooks
                logger.info("Create the ClearBooks customer")
                cb_customer = scoro.clearbooks_customer(customer)
                cb_cust_id = clearbooks.create_customer(cb_customer)
                clearbooks_customers[cust_name] = cb_cust_id

            # Get the invoice project
            if invoice.get("project_id"):
                logger.info("Get the project")
                project = scoro.project(invoice.get("project_id"))
                if project:
                    invoice["project_name"] = project.get("description", "")
            else:
                invoice["project_name"] = ""

            # Map fields and create the invoice in ClearBooks
            logger.info("Create the invoice in ClearBooks")
            cb_invoice = scoro.clearbooks_invoice(cb_cust_id, invoice, clearbooks_accounts)
            cb_inv = clearbooks.create_invoice(cb_invoice)

            # Update the Scoro invoice to show that it has been processed
            logger.info("Update the Scoro invoice")
            response = scoro.update_invoice(invoice, cb_inv["invoice_number"])

        except Exception as e:
            logger.error("Error processing invoice {}: {}".format(inv["no"], e))
            errors.append({"invoice": inv["no"], "error": str(e)})

    return errors


def _read_config():
    return {
        "scoro": {
            "base_url": os.environ.get("SCORO_BASE_URL", "url_not_set/"),
            "api_key": os.environ.get("SCORO_API_KEY", "api_not_set"),
            "lang": os.environ.get("SCORO_LANG", "eng"),
            "company_account_id": os.environ.get("SCORO_ACCOUNT_ID", "account_id"),
        },
        "clearbooks": {
            "api_key": os.environ.get("CLEARBOOKS_API_KEY", "api_not_set"),
        },
    }
