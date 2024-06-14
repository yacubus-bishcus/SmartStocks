from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from datetime import datetime

class WordPrinter:
    _instance = None

    def __new__(cls, filename, debug=False):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.filename = filename
            cls._instance.debug = debug
            cls._instance.doc = Document()

        return cls._instance


    def __del__(self):
        if self.debug:
            print("Closing: ", self.filename)
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
        # Creates a table in a word document from a pandas dataframe (content)
        self.doc.add_heading(heading, level=1)
        table = self.doc.add_table(rows=content.shape[0]+1, cols=content.shape[1])
        for i, column in enumerate(content.columns):
            table.cell(0, i).text = column
        for index, row in content.iterrows():
            for i, value in enumerate(row):
                table.cell(index+1, i).text = str(value)

    def create_executive_summary(self, top_performers, research_performers):
        self.executive_summary = "EXECUTIVE SUMMARY: This report checked the \
        user list provided in Table 3. Additionally, research was conducted on \
        the tickers provided in Table 4. Your top performing stocks are " + top_performers + \
        ". The algorithm projects the following researched stocks as the top potential performers " \
        + research_performers + ". The top performers are summarized in Table 1 and \
        Table 2 respectively."


    def create_document_heading(self):
        # creates default document heading for montly reports
        header = "Stock Market Monthly Report"
        current_date_time = datetime.now()
        current_date = current_date_time.date()
        header_date = "Report Date: " + str(current_date)
        self.write(header, font_size=24, bold=True, underline=True, alignment=WD_PARAGRAPH_ALIGNMENT.CENTER)
        self.write(header_date, color=(128,0,0))
        self.write(self.executive_summary)

    def create_document_tables(self, user_list=None, research_list=None, top_perf=None, research_top=None):
        if top_perf is not None:
            self.write_table(top_perf, "TABLE 1. User Top Performers")
        if research_top is not None:
            self.write_table(research_top, "TABLE 2. Research Top Performers")
        if user_list is not None:
            self.write_table(user_list, "TABLE 3. User Listed Stocks")
        if research_list is not None:
            self.write_table(research_list, "TABLE 4. Research Listed Stocks")

    def remove_invalid_characters(self, content):
        return content.encode('ascii', 'ignore').decode('ascii')

    def save(self):
        self.doc.save(self.filename)

class MyOutput:
    def __init__(self, filename, debug=False):
        self.filename = filename
        self.debug = debug

    def __del__(self):
        if self.debug:
            print("Closing: ", self.filename)
        pass

    def write_to_word_file(self, content):
        # Create a new Document object
        self.doc = Document()

        # Add content to the document
        self.doc.add_paragraph(content)

        # Save the document to the specified output file
        self.doc.save(self.filename)
