from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from datetime import datetime
import os

def generate_essay_pdf(essay):
    """Generate a PDF file for the essay"""
    
    filename = f"essays/{essay['id']}.pdf"
    os.makedirs("essays", exist_ok=True)
    
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor='#1f4788',
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    meta_style = ParagraphStyle(
        'Meta',
        parent=styles['Normal'],
        fontSize=10,
        textColor='#666666',
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    content_style = ParagraphStyle(
        'Content',
        parent=styles['Normal'],
        fontSize=11,
        alignment=TA_LEFT,
        spaceAfter=12,
        leading=16
    )
    
    author_style = ParagraphStyle(
        'Author',
        parent=styles['Normal'],
        fontSize=9,
        textColor='#999999',
        spaceAfter=20,
        alignment=TA_LEFT
    )
    
    story.append(Paragraph(essay['topic'], title_style))
    
    # Handle created_at - it might be datetime object or string
    try:
        if isinstance(essay['created_at'], str):
            created_date = datetime.fromisoformat(essay['created_at']).strftime("%B %d, %Y")
        else:
            # Already a datetime object
            created_date = essay['created_at'].strftime("%B %d, %Y")
    except Exception as e:
        created_date = "Unknown date"
    
    meta_info = f"Created: {created_date}"
    story.append(Paragraph(meta_info, meta_style))
    
    story.append(Spacer(1, 0.3*inch))
    
    first_content = essay.get('first_content', '')
    second_content = essay.get('second_content', '')
    full_content = f"{first_content}\n\n{second_content}"
    story.append(Paragraph(full_content, content_style))
    
    story.append(Spacer(1, 0.3*inch))
    
    creator_name = essay.get('creator_name', 'Unknown')
    story.append(Paragraph(f"<b>Contributors:</b>", author_style))
    story.append(Paragraph(f"1. {creator_name} (Opening)", author_style))
    
    # Add all partners
    if essay.get('partners'):
        for i, partner in enumerate(essay['partners'], start=2):
            story.append(Paragraph(f"{i}. {partner['name']} (Continuation)", author_style))
    else:
        # Fallback for old format essays
        if essay.get('partner_name'):
            story.append(Paragraph(f"2. {essay['partner_name']} (Development)", author_style))
    
    doc.build(story)
    
    return filename
