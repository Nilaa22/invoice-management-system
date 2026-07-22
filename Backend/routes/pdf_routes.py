# 

import logging
import os

from flask import (
    Blueprint,
    jsonify,
    request,
    send_file
)

from io import BytesIO

from playwright.sync_api import (
    sync_playwright
)


pdf_bp = Blueprint(
    "pdf_bp",
    __name__
)


@pdf_bp.route(
    "/generate-invoice-pdf",
    methods=["POST"]
)
def generate_invoice_pdf():
    data = request.get_json(
        silent=True
    ) or {}

    html_content = data.get(
        "html_content"
    )

    file_name = str(
        data.get(
            "file_name",
            "invoice.pdf"
        )
    ).strip()

    if not html_content:
        return jsonify({
            "message":
                "Invoice HTML is required"
        }), 400

    if not file_name:
        file_name = "invoice.pdf"

    if not file_name.lower().endswith(
        ".pdf"
    ):
        file_name = f"{file_name}.pdf"

    browser = None

    try:
        browser_directory = os.environ.get(
            "PLAYWRIGHT_BROWSERS_PATH",
            ""
        )

        logging.info(
            "PLAYWRIGHT_BROWSERS_PATH=%s",
            browser_directory
        )

        with sync_playwright() as playwright:
            executable_path = (
                playwright.chromium
                .executable_path
            )

            logging.info(
                "Expected Chromium executable: %s",
                executable_path
            )

            logging.info(
                "Chromium executable exists: %s",
                os.path.exists(
                    executable_path
                )
            )

            if not os.path.exists(
                executable_path
            ):
                raise RuntimeError(
                    "Chromium executable was not "
                    "found at the expected runtime "
                    f"path: {executable_path}"
                )

            browser = playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu"
                ]
            )

            page = browser.new_page(
                viewport={
                    "width": 794,
                    "height": 1123
                }
            )

            page.set_content(
                html_content,
                wait_until="networkidle",
                timeout=60000
            )

            page.emulate_media(
                media="print"
            )

            pdf_bytes = page.pdf(
                format="A4",
                print_background=True,
                prefer_css_page_size=True,
                margin={
                    "top": "10mm",
                    "right": "12mm",
                    "bottom": "10mm",
                    "left": "12mm"
                }
            )

            browser.close()
            browser = None

        return send_file(
            BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=file_name
        )

    except Exception as error:
        logging.exception(
            "Invoice PDF generation failed"
        )

        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass

        return jsonify({
            "message":
                "Unable to generate PDF",

            "error":
                str(error)
        }), 500