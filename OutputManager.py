from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from fpdf import FPDF
import os
from colorama import Fore, Style
import pkg_resources
import pandas as pd
import matplotlib.pyplot as plt
import logging
from tqdm import tqdm
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import ssl
from docx.oxml.ns import nsdecls
#from docx.oxml import register_namespace

logger = logging.getLogger(__name__)
#register_namespace('w', 'http://schemas.openxmlformats.org/wordprocessingml/2006/main')

class WordPrinter:
    _instance = None

    def __new__(cls, filename):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._create_report_card()
            if filename is not None:
                if not filename.endswith(".docx"):
                    cls._instance.filename = filename + ".docx"
                else:
                    cls._instance.filename = filename

                cls._instance.filepath = pkg_resources.resource_filename('StockApp.output', cls._instance.filename)
            cls._instance.doc = Document()

        return cls._instance

    def __del__(self):
        pass

    def _create_report_card(self):
        # the report card is a dictionary data structure with every output for the report
        self.report_card = {'filename':'', 'filepath':'',
        'top_performers':[], 'table_sheet_name':'', 'figures':[] ,'best':'',
        'total_stocks':0,'mse':0,'r_squared':0
        } # add any additional report outputs to the report card

    def add_to_report_card(self, key, value):
        self.report_card[key] = value

    def grab_report_card_value(self, key):
        return self.report_card[key]

    def write(self, content, font_size=12, font_name='Arial', bold=False, italic=False, underline=False, color=None, alignment=None):
        content = self.remove_invalid_characters(content)
        paragraph = self.doc.add_paragraph()
        run = paragraph.add_run(content)
        # Font size
        run.font.size = Pt(font_size)
        # Font name
        run.font.name = font_name
        # Bold, italic, underline
        run.bold = bold
        run.italic = italic
        run.underline = underline
        # Color
        if color:
            run.font.color.rgb = RGBColor(*color) # convert (r,g,b) on scale 0 - 255

        # Alignment
        if alignment:
            paragraph.alignment = alignment

    def write_table(self, content, heading):
        content = content.astype(str)
        self.doc.add_page_break()
        self.doc.add_heading(heading, level=1)

        # Add the table with correct number of columns
        table = self.doc.add_table(rows=content.shape[0] + 1, cols=content.shape[1] - 1)  # Adjusted for skipping first column
        table.style = 'Table Grid'
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        # Set column headers, skipping the first column
        for i, column in enumerate(content.columns[1:], start=1):
            table.cell(0, i - 1).text = str(column)

        # Populate table with data, skipping the first column
        for index, row in content.iterrows():
            for i, value in enumerate(row[1:], start=1):
                try:
                    cell_value = str(value)
                    table.cell(index + 1, i - 1).text = cell_value

                    # Apply bold formatting to numeric columns where applicable
                    if content.dtypes[i] in ['float64', 'int64']:
                        # Find the index of the row with maximum value in 'WAM' column
                        if index == content['WAM'].astype(float).idxmax():
                            table.cell(index + 1, i - 1).paragraphs[0].runs[0].font.bold = True

                    # Apply red font color to negative numeric values
                    if content.dtypes[i] in ['float64', 'int64']:
                        if cell_value.lstrip('-').replace('.', '', 1).isdigit() and float(value) < 0:
                            table.cell(index + 1, i - 1).paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 0, 0)

                    # Apply shading based on comparison of numeric columns
                    if content.dtypes[i] in ['float64', 'int64']:
                        if i < len(row) - 2 and content.dtypes[i + 1] in ['float64', 'int64']:
                            if float(row[i]) > float(row[i + 1]):
                                shading_elm = table.cell(index + 1, i - 1)._element
                                shading = shading_elm.xpath('.//w:shd')
                                if not shading:
                                    shading = OxmlElement('w:shd')
                                    shading.set(qn('w:fill'), '00FF00')  # Green color code
                                    shading_elm.append(shading)
                            elif float(row[i]) < float(row[i + 1]):
                                shading_elm = table.cell(index + 1, i - 1)._element
                                shading = shading_elm.xpath('.//w:shd')
                                if not shading:
                                    shading = OxmlElement('w:shd')
                                    shading.set(qn('w:fill'), 'FF0000')  # Red color code
                                    shading_elm.append(shading)

                except (TypeError, ValueError) as e:
                    # Handle specific exceptions like type conversion errors
                    error_msg = f"Error handling value at index {index}, column {content.columns[i+1]}: {e}"
                    logger.exception(error_msg)
                    table.cell(index + 1, i - 1).text = ""  # Set empty string if conversion fails or error

        # Adjust font size for all cells
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.size = Pt(6)

        # Additional styling and adjustments can be uncommented and modified as needed

        # Adjust column width and cell padding
        # for row in table.rows:
        #     for cell in row.cells:
        #         cell_width = Pt(60)
        #         self.set_column_width(cell, cell_width)
        #         cell_margin = OxmlElement('w:tcMar')
        #         cell_margin.set(qn('w:top'), '100')
        #         cell_margin.set(qn('w:start'), '100')
        #         cell_margin.set(qn('w:bottom'), '100')
        #         cell_margin.set(qn('w:end'), '100')
        #         cell._element.get_or_add_tcPr().append(cell_margin)

        # Return or save the document as needed

    def set_column_width(self, cell, width):
        """
        Set the width of a table cell in a Word document.

        Parameters:
        - cell: The cell in which to set the width.
        - width: The width of the cell in points (Pt).
        """
        cell.width = width

    def create_explanation_statement(self):
        self.write("For each stock your requested models were applied to deliver two resulting metrics. "\
        "Metric one, the Weighted Aggregate Merit or WAM is a simple weighted sum of the normalized performance measures."\
        " The performance measures were normalized using the Yeo-Johnson power transformation due to the assumption that stocks do not behave normally.  "\
        "The second performance metric, Supervised Aggregate Merit (SAM) was derived from a regression analysis with test size being 10 percent."\
        " Stocks with a higher WAM and/or SAM are more likely to succeed than others."\
        " Additionally, a Monte-Carlo Futures Price 'MCFP' was determined."\
        " The simulation was conducted used an averaged Gaussian/Poisson-Gamma distribution."\
        )

    def create_document_heading(self):
        # creates default document heading for montly reports
        self.add_to_report_card('header', 'Stock Market Report Powered by Smart Stocks')
        disclaimer = "DISCLAIMER: The creator referenced shall be known as Jacob E Bickus. " \
        "The Application referenced shall be known as Smart Stocks. " \
        "\nThe Content is for informational purposes only, you should not construe any such " \
        "information or other material as legal, tax, investment, financial, or other advice."
        "Nothing contained on the Application constitutes a solicitation, recommendation," \
        " endorsement, or offer by the creator or any third party service provider to buy" \
        " or sell any securities or other financial instruments in this or" \
        " in in any other jurisdiction in which such solicitation or offer would be unlawful" \
        " under the securities laws of such jurisdiction. All Content on this site is" \
        " information of a general nature and does not address the circumstances of"\
        " any particular individual or entity. Nothing in the Site constitutes professional"\
        " and/or financial advice, nor does any information on the Site constitute a"\
        " comprehensive or complete statement of the matters discussed or the law relating thereto."\
        " The creator is not a fiduciary by virtue of any person’s use of or access to the Site or Content."\
        " You alone assume the sole responsibility of evaluating the merits and risks associated with"\
        " the use of any information or other Content on the Site before making any decisions based on such"\
        " information or other Content. In exchange for using the Site, you agree not"\
        " to hold the creator, its affiliates or any third party service provider liable"\
        " for any possible claim for damages arising from any decision you make based"\
        " on information or other Content made available to you through the Application."

        self.add_to_report_card('disclaimer', disclaimer)
        current_date_time = datetime.now()
        current_date = current_date_time.date()
        header_date = "Report Date: " + str(current_date)
        self.add_to_report_card('date',header_date)
        self.write(self.report_card['header'], font_size=24, bold=True, underline=True, alignment=WD_PARAGRAPH_ALIGNMENT.CENTER)
        self.write(header_date, color=(128,0,0))
        self.write(self.report_card['disclaimer'], font_size=8)
        self.write("\nEXECUTIVE SUMMARY:")

    def create_document_tables(self, user_list=None, research_list=None, top_perf=None, research_top=None, table_count=0):
        if table_count == 4:
            if top_perf is not None:
                self.write_table(top_perf, "TABLE 1. User Top Performers")
            if research_top is not None:
                self.write_table(research_top, "TABLE 2. Research Top Performers")
            if user_list is not None:
                self.write_table(user_list, "TABLE 3. User Listed Stocks")
            if research_list is not None:
                self.write_table(research_list, "TABLE 4. Research Listed Stocks")
        elif table_count == 2:
            # if top_perf is not None:
            #     self.write_table(top_perf, "TABLE 1. User Top Performers")
            if research_top is not None:
                self.write_table(research_top, "TABLE 1. Research Top Performers")
            if user_list is not None:
                self.write_table(user_list, "TABLE 2. User Listed Stocks")
            if research_list is not None:
                self.write_table(research_list, "TABLE 2. Research Listed Stocks")
        else:
            print(Fore.RED + "StockOutputManager::create_document_tables FATAL ERROR --> Table Count must equal 2 or 4." + Style.RESET_ALL)

    def remove_invalid_characters(self, content):
        return content.encode('ascii', 'ignore').decode('ascii')

    def save(self):
        self.doc.save(self.filepath)

    # takes input stock name (str) and a list of figures (figure objs)
    def add_plots_to_word(self, stock_name, figures):
        logger.info(f"Creating {stock_name} Plots")
        for figure in tqdm(figures, desc="Figures"):
            if figure is not None:
                self.doc.add_heading(stock_name, level=1)
                temp_file = pkg_resources.resource_filename('StockApp.output', "figure.png")
                figure.savefig(temp_file, bbox_inches='tight')
                self.doc.add_picture(temp_file, width=Inches(6))
                plt.close(figure)
                os.remove(temp_file)
                self.doc.add_page_break()
            else:
                logger.warning("Tried to Add NoneType Figure to Word doc. Skipping model figure.")
        logger.info(f"{stock_name} Plots Created.")


class OutputHandler:
    def __init__(self, filename):
        if not filename.endswith(".docx"):
            self.filename = filename + ".docx"
        else:
            self.filename = filename
        self.filepath = pkg_resources.resource_filename('StockApp.output', self.filename)

    def __del__(self):
        pass

    def convert_word_to_pdf(self):
        # Check if the Word document exists
        if not os.path.exists(self.filepath):
            print(Fore.RED + f"OutputManager::convert_word_to_pdf Error: File '{self.filepath}' not found." + Style.RESET_ALL)
            return
        # Read the Word document
        doc = Document(self.filepath)

        # Create a PDF object
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Add each paragraph from the Word document to the PDF
        for para in doc.paragraphs:
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt=para.text, ln=True)
        pdf_filename = self.filepath.replace(".doc", ".pdf")
        # Save the PDF
        pdf.output(pdf_filename)

    def email_file(self, email_to, smtp_username, smtp_password, filename=None, email_subject="Smart Stock Report", email_body="See attached.", smtp_server="smtp.gmail.com", smtp_port=587):
        # Create a multipart message
        if filename is None:
            filename = self.filepath

        msg = MIMEMultipart()
        msg['From'] = smtp_username
        msg['To'] = email_to
        msg['Subject'] = email_subject

        # Add body to email
        msg.attach(MIMEText(email_body, 'plain'))

        # Open and attach the file to the email
        attachment = open(filename, "rb")
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {filename}")
        msg.attach(part)
        # SSL context configuration
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        # Send the email
        try:
            # Connect to SMTP server and send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(smtp_username, smtp_password)
                server.sendmail(smtp_username, email_to, msg.as_string())
                print("Email Sent!")
        except Exception as e:
            print(f"Error sending email: {e}")

    def write_table(self, content, heading, output_file):
        # Creates a table in a word document from a pandas dataframe (content)
        content = content.astype(str)
        doc = Document()
        doc.add_heading(heading, level=1)
        table = doc.add_table(rows=content.shape[0] + 1, cols=content.shape[1] - 1)  # Adjust cols to skip first column

        # Set column headers, skipping the first column
        for i, column in enumerate(content.columns[1:], start=1):
            table.cell(0, i - 1).text = str(column)

        # Populate table with data, skipping the first column
        for index, row in content.iterrows():
            for i, value in enumerate(row[1:], start=1):
                try:
                    # Try to convert value to string
                    table.cell(index + 1, i - 1).text = str(value)
                except Exception as e:
                    # If conversion fails, handle the error
                    error_msg = f"Error converting value at index {index}, column {content.columns[i]}: {e}"
                    print(error_msg)
                    table.cell(index + 1, i - 1).text = ""  # Set empty string if conversion fails

        doc.save(output_file)
