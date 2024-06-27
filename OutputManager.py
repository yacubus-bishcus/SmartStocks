from docx import Document
from docx.shared import Pt, RGBColor, Inches
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

# My Modules 
from Model_Handler import Model_Handler

logger = logging.getLogger(__name__)


class Email:
    def __init__(self, filename):
        if not filename.endswith(".docx"):
            self.filename = filename + ".docx"
        else:
            self.filename = filename
        self.filepath = pkg_resources.resource_filename('output', self.filename)

    def __del__(self):
        pass

    @property 
    def filename(self):
        return self._filename  
    
    @filename.setter 
    def filename(self):
        self.filename = self._filename 

    @property 
    def filepath(self):
        return self._filepath 
    
    @filepath.setter 
    def filepath(self, value):
        self._filepath = value 

    def email(self, email_to, smtp_username, smtp_password, email_subject, email_body, filename=None, smtp_server="smtp.gmail.com", smtp_port=587):
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
        if filename is not None: 
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

class WordPrinter: # manager for anything printing to word doc 
    _instance = None

    def __new__(cls, filename, directory):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.init_instance(filename, directory)
        return cls._instance

    def init_instance(self, filename, directory):
        if not filename.endswith(".docx"):
            self.filename = filename + ".docx"
        else:
            self.filename = filename

        self.filepath = pkg_resources.resource_filename(directory, self.filename)
        self.doc = Document()

    def __init__(self, filename, directory):
        pass

    def __del__(self):
        pass
    
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

    def set_column_width(self, cell, width):
        """
        Set the width of a table cell in a Word document.

        Parameters:
        - cell: The cell in which to set the width.
        - width: The width of the cell in points (Pt).
        """
        cell.width = width

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

    def remove_invalid_characters(self, content):
        return content.encode('ascii', 'ignore').decode('ascii')

    def save(self):
        self.doc.save(self.filepath)

    # takes input name (str) and a list of figures (figure objs)
    def create_plots(self, name, figures):
        logger.info(f"Creating {name} Plots")
        if figures is not None:
            for figure in tqdm(figures, desc="Figures"):
                if figure is not None:
                    self.doc.add_heading(name, level=1)
                    temp_file = pkg_resources.resource_filename('output', "figure.png")
                    figure.savefig(temp_file, bbox_inches='tight')
                    self.doc.add_picture(temp_file, width=Inches(6))
                    plt.close(figure)
                    os.remove(temp_file)
                    self.doc.add_page_break()
                else:
                    logger.warning("Tried to Add NoneType Figure to Word doc. Skipping model figure.")
        else:
            logger.warning("Tried to Add NoneType Figure to Word doc. Skipping model figure.")
        
        logger.info(f"{name} Plots Created.")

class SmartStocksOutput(WordPrinter, Email):
    def __new__(cls, filename, directory, *args, **kwargs):
        return super(SmartStocksOutput, cls).__new__(cls, filename, directory)

    def __init__(self, filename, directory, args):
        WordPrinter.__init__(self, filename=filename, directory=directory)
        Email.__init__(self, filename=filename)
        self.args = args
        self._filename = filename 
        self._directory = directory 
        self._args = args 
        self._filepath = pkg_resources.resource_filename(directory, self.filename)
        self._top_performers = None 
        self._table_sheet_name = None 
        self._figures = None 
        self._total_stocks = None 
        self._best = None 
        self._mse = None 
        self._r_squared = None 

    def __del__(self):
        pass 

    @property 
    def filename(self) -> str:
        return self._filename 
    
    @filename.setter 
    def filename(self, value):
        self._filename = value 

    @property 
    def directory(self):
        return self._directory 
    
    @directory.setter 
    def directory(self, value):
        self._directory = value 

    @property 
    def args(self):
        return self._args 
    
    @args.setter 
    def args(self, value):
        self._args = value 

    @property 
    def filepath(self)-> str:
        return self._filepath 
    
    @filepath.setter 
    def filepath(self, value):
        self._filepath = value 

    @property 
    def top_performers(self) -> pd.DataFrame:
        return self._top_performers 
    
    @top_performers.setter 
    def top_performers(self, value):
        self._top_performers = value 

    @property 
    def table_sheet_name(self):
        return self._table_sheet_name 
    
    @table_sheet_name.setter
    def table_sheet_name(self, value):
        self._table_sheet_name = value 

    @property 
    def figures(self) -> list:
        return self._figures 
    
    @figures.setter
    def figures(self, value):
        self._figures = value 

    @property 
    def best(self):
        return self._best  
    
    @best.setter
    def best(self, value):
        self._best = value 

    @property 
    def total_stocks(self) -> int:
        return self._total_stocks 
    
    @total_stocks.setter 
    def total_stocks(self, value):
        self._total_stocks = value 
        
    @property 
    def mse(self) -> float:
        return self._mse  
    
    @mse.setter 
    def mse(self, value):
        self._mse = value 

    @property
    def r_squared(self) -> float:
        return self._r_squared
    
    @r_squared.setter
    def r_squared(self, value):
        self._r_squared = value 

    def smartstock_heading(self):
        # creates default document heading for montly reports
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
        " The creator is not a fiduciary by virtue of any persons use of or access to the Site or Content."\
        " You alone assume the sole responsibility of evaluating the merits and risks associated with"\
        " the use of any information or other Content on the Site before making any decisions based on such"\
        " information or other Content. In exchange for using the Site, you agree not"\
        " to hold the creator, its affiliates or any third party service provider liable"\
        " for any possible claim for damages arising from any decision you make based"\
        " on information or other Content made available to you through the Application."

   
        current_date_time = datetime.now()
        current_date = current_date_time.date()
        header_date = "Report Date: " + str(current_date)
        self.write("Report Brought to you by SMART STOCKS created by Jacob E Bickus", font_size=36, bold=True, underline=True)
        self.write(header_date, color=(128,0,0))
        self.write(disclaimer, font_size=8)
        self.write("\nEXECUTIVE SUMMARY:")

    def smartstock_tables(self, user_list=None, research_list=None, top_perf=None, research_top=None, table_count=0):
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

    def smartstock_explanation_statement(self):
        self.write("For each stock your requested models were applied to deliver two resulting metrics. "\
        "Metric one, the Weighted Aggregate Merit or WAM is a simple weighted sum of the normalized performance measures."\
        " The performance measures were normalized using the Yeo-Johnson power transformation due to the assumption that stocks do not behave normally.  "\
        "The second performance metric, Supervised Aggregate Merit (SAM) was derived from a regression analysis with test size being 10 percent."\
        " Stocks with a higher WAM and/or SAM are more likely to succeed than others."\
        " Additionally, a Monte-Carlo Futures Price 'MCFP' was determined."\
        " The simulation was conducted used the Merton Jump Diffusion Model."\
        )

    def smartstock_plots(self, Stock_best, stock_df, stds_df, analysis, market_df=None, market_stds=None, market_data=None):
        filename = ""
        figures = []
        if Stock_best is None:
            logger.warning("No best stock was found. Skipping plotting.")
            return

        if self.filename.endswith(".docx"):
            filename = self.filename.replace(".docx", ".png")
            
        filepath = pkg_resources.resource_filename(self.directory, filename)

        # here the model handler will be based off the user's input for time_delta
        number_one_model = Model_Handler(Stock_list=Stock_best, market_data=market_data, risk_free_rate=analysis.risk_free_rate, args=self.args)
        number_one_model.pass_futures_data(stock_df, stds_df)
        number_one_model.pass_futures_market_data(market_df, market_stds)
        #number_one_model.pass_market_stock(market_index.index)

        if self.args.simulations > 0:
            number_one_model.add_all_plotting_models(True)
        else:
            number_one_model.add_all_plotting_models(False)

        figures = number_one_model.plot_catcher(filepath)

        return figures
    
    def write_to_excel(self, df, sheet_name, data_w_dates=False): 
        if df is None:
            logger.warning(Fore.YELLOW + "Write To excel received nonetype (empty) dataframe." + Style.RESET_ALL)
            return 
        
        if data_w_dates:
            df = self.make_dates_timezone_unaware(df)

        # Define the file path
        if self.args.output.endswith(".docx"):
            filename = self.args.output.replace(".docx", ".xlsx")
        else:
            filename = self.args.output + ".xlsx"

        filepath = pkg_resources.resource_filename(self.directory, filename)
        
        try:
            # Check if the file already exists and is a valid Excel file
            if os.path.exists(filepath):
                with pd.ExcelWriter(filepath, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                    # Write the DataFrame to the specified sheet
                    logger.warning(Fore.YELLOW + f"Replacing data in {filepath}" + Style.RESET_ALL)
                    df.to_excel(writer, index=True, sheet_name=sheet_name)
            else:
                try:
                    # Create a new workbook and write the DataFrame to it
                    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                        df.to_excel(writer, index=True, sheet_name=sheet_name)
                        
                except Exception as e:
                    logger.exception(Fore.RED + f"An error occuring while writing to sheet {sheet_name} in new file {filepath}. Error: {e}." + Style.RESET_ALL)
                    logger.warning(Fore.YELLOW + "Printing dataframe..." + Style.RESET_ALL)
                    logger.warning(df)

        except KeyError as e:
            if "[Content_Types].xml" in str(e):
                logger.error(Fore.RED + f"File {filepath} is corrupt or not a valid Excel file. Creating a new file." + Style.RESET_ALL)
                # Create a new workbook and write the DataFrame to it
                with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                    df.to_excel(writer, index=True, sheet_name=sheet_name)
        except Exception as e:
            logger.exception(Fore.RED + f"An error occurred while writing to Excel: {e}" + Style.RESET_ALL)

    def make_dates_timezone_unaware(self, df):
        # Check if the index is datetime and has timezone info
        if isinstance(df.index, pd.DatetimeIndex):
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)

        return df 