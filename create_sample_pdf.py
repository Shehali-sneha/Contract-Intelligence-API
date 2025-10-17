#!/usr/bin/env python3
"""Create a sample contract PDF for testing."""

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def create_sample_contract():
    """Create a sample contract PDF."""
    c = canvas.Canvas("sample_contract.pdf", pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, height - 100, "SERVICE AGREEMENT")
    
    # Content
    c.setFont("Helvetica", 11)
    y = height - 150
    
    lines = [
        "This Service Agreement ('Agreement') is entered into between",
        "ABC Corporation and XYZ Solutions on January 15, 2024.",
        "",
        "Term: This agreement shall remain in effect for a period of 12 months",
        "from the effective date.",
        "",
        "Governing Law: This agreement shall be governed by the laws of California.",
        "",
        "Payment Terms: Client agrees to pay within Net 30 days of invoice date.",
        "Payment shall be made via wire transfer or ACH.",
        "",
        "Termination: Either party may terminate this agreement with 30 days",
        "written notice. Upon termination, all outstanding payments become due.",
        "",
        "Auto-Renewal: This agreement automatically renews for successive 12-month",
        "periods unless either party provides written notice at least 30 days",
        "prior to the end of the then-current term.",
        "",
        "Confidentiality: Both parties agree to maintain the confidentiality of",
        "all proprietary information shared during the course of this agreement.",
        "",
        "Indemnity: Each party shall indemnify and hold harmless the other party",
        "from any claims arising from their breach of this agreement.",
        "",
        "Liability Cap: The total liability of either party under this agreement",
        "shall not exceed USD $100,000.",
        "",
        "",
        "Signatories:",
        "John Smith, CEO, ABC Corporation",
        "Jane Doe, President, XYZ Solutions",
    ]
    
    for line in lines:
        c.drawString(100, y, line)
        y -= 15
        if y < 100:  # New page if needed
            c.showPage()
            y = height - 100
            c.setFont("Helvetica", 11)
    
    c.save()
    print("✅ Sample contract created: sample_contract.pdf")

if __name__ == "__main__":
    try:
        create_sample_contract()
    except ImportError:
        print("⚠️  reportlab not installed. Installing...")
        import subprocess
        subprocess.check_call(["pip", "install", "-q", "reportlab"])
        create_sample_contract()
