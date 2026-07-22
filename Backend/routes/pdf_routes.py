# from flask import (
#     Blueprint,
#     request,
#     jsonify,
#     send_file
# )

# from playwright.sync_api import (
#     sync_playwright
# )

# from io import BytesIO


# pdf_bp = Blueprint(
#     "pdf_bp",
#     __name__
# )


# @pdf_bp.route(
#     "/generate-invoice-pdf",
#     methods=["POST"]
# )
# def generate_invoice_pdf():
#     data = request.get_json(
#         silent=True
#     ) or {}

#     html_content = data.get(
#         "html_content"
#     )

#     file_name = data.get(
#         "file_name",
#         "invoice.pdf"
#     )

#     if not html_content:
#         return jsonify({
#             "message":
#                 "Invoice HTML is required"
#         }), 400

#     if not file_name.lower().endswith(
#         ".pdf"
#     ):
#         file_name = f"{file_name}.pdf"

#     try:
#         with sync_playwright() as playwright:
#             # browser = (
#             #     playwright.chromium.launch(
#             #         headless=True
#             #     )
#             # )
#             browser = playwright.chromium.launch(
#     channel="chromium",
#     headless=True,
#     args=[
#         "--no-sandbox",
#         "--disable-setuid-sandbox",
#         "--disable-dev-shm-usage",
#     ],
# )

#             page = browser.new_page()

#             page.set_content(
#                 html_content,
#                 wait_until="networkidle"
#             )

#             page.emulate_media(
#                 media="print"
#             )

#             pdf_bytes = page.pdf(
#                 format="A4",

#                 print_background=True,

#                 prefer_css_page_size=True,

#                 margin={
#                     "top": "10mm",
#                     "right": "12mm",
#                     "bottom": "10mm",
#                     "left": "12mm"
#                 }
#             )

#             browser.close()

#         return send_file(
#             BytesIO(pdf_bytes),

#             mimetype="application/pdf",

#             as_attachment=True,

#             download_name=file_name
#         )

#     except Exception as error:
#         return jsonify({
#             "message":
#                 "Unable to generate PDF",

#             "error":
#                 str(error)
#         }), 500
from flask import (
    Blueprint,
    request,
    jsonify,
    send_file
)

from playwright.sync_api import (
    sync_playwright
)

from io import BytesIO
import logging


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
        logging.info(
            "Starting invoice PDF generation"
        )

        with sync_playwright() as playwright:
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

        logging.info(
            "Invoice PDF generated successfully"
        )

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