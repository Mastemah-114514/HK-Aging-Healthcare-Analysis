from pypdf import PdfReader
import re
try:
    reader = PdfReader(r'C:\Users\Mastemah\Downloads\111.pdf')
    text = ''.join(page.extract_text() for page in reader.pages)
    ips = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', text)
    print("Found IPs in PDF:", ips)
except Exception as e:
    print("Error:", e)
