import streamlit as st
import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_path
import camelot
import io
from PIL import Image
from groq import Groq
from fpdf import FPDF
import os

# Initialize Groq API
GROQ_API_KEY = st.secrets.key.G_api
client = Groq(api_key=GROQ_API_KEY)

def extract_text_from_pdf(pdf_file):
    pdf_path = "uploaded_file.pdf"
    with open(pdf_path, "wb") as f:
        f.write(pdf_file.getbuffer())
    
    doc = fitz.open(pdf_path)
    extracted_text = ""

    for page_num in range(min(doc.page_count, 20)):  # Limit to 20 pages
        page = doc.load_page(page_num)
        text = page.get_text()
        extracted_text += f"\n\nPage {page_num + 1}\n{text}"

        image_list = page.get_images(full=True)
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            image = Image.open(io.BytesIO(image_bytes))
            ocr_text = pytesseract.image_to_string(image)
            extracted_text += ocr_text

        tables = camelot.read_pdf(pdf_path, pages=str(page_num + 1))
        for table in tables:
            extracted_text += table.df.to_string()

        # Summarize the text and save it in a PDF
        summary = summarize_text(extracted_text)
        generate_pdf(summary, page_num + 1)

    return "Summarization complete. Download the PDF below."

def summarize_text(text, model="llama-3.1-70b-versatile"):
    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": "Summarize this page in 15-20 lines under the heading of summary. You have to summarize, even if there are different, unlike topics on that page. (Kindly provide the response in proper paragraphing). However, if there is no text, then print Nothing to summarize. Additionally, after summarizing the text, enlist difficult terms up to 15, along with their single line meaning." + text}],
        model=model,
    )
    return chat_completion.choices[0].message.content

def generate_pdf(summary, page_number):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 7, f"Summary of Page {page_number}\n\n" + summary.encode('utf-8').decode('latin-1'))
    pdf.output(f"output.pdf", "F")

# Streamlit app setup
st.title("PDF Summarizer")
st.write("Upload a PDF file (up to 20 pages) to summarize its content.")

uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

if uploaded_file is not None:
    st.write("Processing the PDF file...")
    message = extract_text_from_pdf(uploaded_file)
    
    st.success(message)
    
    # Provide download link for the summarized PDF
    with open("output.pdf", "rb") as f:
        st.download_button("Download Summarized PDF", f, file_name="output.pdf")
