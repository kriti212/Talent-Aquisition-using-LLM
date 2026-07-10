import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def create_presentation_pdf(output_path):
    # Setup document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#4f46e5'),
        alignment=1, # Center
        spaceAfter=15
    )
    
    h1_style = ParagraphStyle(
        'SecHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1e293b'),
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#334155'),
        spaceAfter=6
    )
    
    bullet_style = ParagraphStyle(
        'BulletCustom',
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )
    
    quote_style = ParagraphStyle(
        'QuoteStyle',
        parent=body_style,
        leftIndent=10,
        textColor=colors.HexColor('#475569'),
        fontName='Helvetica-Oblique'
    )
    
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white
    )
    
    table_body_style = ParagraphStyle(
        'TableBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#1e293b')
    )
    
    story = []
    
    # Title
    story.append(Paragraph("Masterclass Presentation Script", title_style))
    story.append(Paragraph("AI-Powered Talent Acquisition Platform", ParagraphStyle('Sub', parent=title_style, fontSize=13, leading=15, textColor=colors.HexColor('#64748b'), spaceAfter=15)))
    story.append(Spacer(1, 5))
    
    # Section 1
    story.append(Paragraph("Part 1: The Pitch (The Hook & Problem) - 2 Minutes", h1_style))
    story.append(Paragraph("<b>Opening Speech Hook:</b>", body_style))
    story.append(Paragraph("\"Good morning, everyone. We have all experienced the friction in the hiring funnel. For recruiters, reading through hundreds of resumes is exhausting and prone to bias. For technical managers, conducting initial phone screens is a massive sink of engineering hours. Today, we are presenting our AI-Powered Talent Acquisition Platform. This isn't just another keyword scanner. We have built an end-to-end intelligent agent that parses candidate profiles semantically, matches them to roles using hybrid vector search, and conducts an interactive, voice-enabled technical screening interview evaluated entirely by an LLM.\"", quote_style))
    story.append(Spacer(1, 5))
    
    # Section 2
    story.append(Paragraph("Part 2: Technical Innovations - 2 Minutes", h1_style))
    story.append(Paragraph("<b>1. Semantic Matching over Keywords</b>: Instead of simple text-matching, we load candidate resumes and job roles as high-dimensional BERT embeddings, calculating semantic similarity to rank candidates on their actual skills, not just buzzwords.", bullet_style))
    story.append(Paragraph("<b>2. Real-Time Voice Compression Pipeline</b>: When the candidate speaks, their voice is captured as WAV, downsampled to 16,000Hz, compressed into an MP3 file using `lameenc` (reducing file size by over 80%), and stored as a lightweight Base64 string in MongoDB. This keeps database storage clean and minimal.", bullet_style))
    story.append(Paragraph("<b>3. High-Availability Fallback Design</b>: If our network connection drops or the LLM server is unreachable, our interview module cycles through a rotating queue of 5 distinct professional questions to protect the candidate's user experience.", bullet_style))
    story.append(Spacer(1, 5))
    
    # Section 3
    story.append(Paragraph("Part 3: Live Demo Script (Step-by-Step) - 4 Minutes", h1_style))
    
    # Live Demo Table Data
    table_data = [
        [
            Paragraph("Phase & Screen", table_header_style),
            Paragraph("Action to Perform", table_header_style),
            Paragraph("Word-for-Word Spoken Script", table_header_style)
        ],
        [
            Paragraph("<b>1. Home Screen</b>", table_body_style),
            Paragraph("Open localhost:8501. Upload a resume PDF. Click 'Process & Match'.", table_body_style),
            Paragraph("<i>'We begin at the Candidate Portal. I will upload this backend developer resume. In the background, our parser extracts clean text and matches it against our job database using BERT embeddings to recommend matched roles.'</i>", table_body_style)
        ],
        [
            Paragraph("<b>2. Job Matching</b>", table_body_style),
            Paragraph("Scroll through recommendations. Select Python Developer and click Apply.", table_body_style),
            Paragraph("<i>'The candidate is presented with their parsed skills and the top 5 recommended roles. I will select the Python Developer role. The system instantly initializes a MongoDB record and generates our first question.'</i>", table_body_style)
        ],
        [
            Paragraph("<b>3. The Interview</b>", table_body_style),
            Paragraph("Click 'Start Recording', speak a 15-sec answer, click 'Stop & Transcribe', then click Submit.", table_body_style),
            Paragraph("<i>'The AI asks a question. I will record my answer. The app uses Google Speech-to-Text to transcribe my voice. Under the hood, this audio is compressed to MP3 and stored as a base64 string in MongoDB.'</i>", table_body_style)
        ],
        [
            Paragraph("<b>4. Preferences</b>", table_body_style),
            Paragraph("Fill out the salary, relocation, and work preference fields. Click Submit.", table_body_style),
            Paragraph("<i>'At the final step, the candidate inputs their job preferences. The app triggers our LLM evaluator, which grades the full transcript, assesses technical depth, soft skills, and provides a structured scorecard.'</i>", table_body_style)
        ],
        [
            Paragraph("<b>5. Recruiter View</b>", table_body_style),
            Paragraph("Open localhost:8502. Select candidate. Play candidate recorded audio.", table_body_style),
            Paragraph("<i>'Now, let's step into the recruiter dashboard. Selecting our candidate displays the detailed AI scorecard. Crucially, I can review the transcript and play the candidate's exact voice answer directly from this browser.'</i>", table_body_style)
        ]
    ]
    
    col_widths = [80, 140, 284]
    demo_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    demo_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#4f46e5')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#f8fafc'), colors.white]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
    ]))
    
    story.append(demo_table)
    story.append(Spacer(1, 5))
    
    # Section 4
    story.append(Paragraph("Part 4: Expert Q&A Defense Strategy", h1_style))
    story.append(Paragraph("<b>Q: Why separate the candidate portal and admin portal into two apps?</b>", body_style))
    story.append(Paragraph("<i>Answer: Security and separation of concerns. Candidates should never have access to recruitment analytics, scorecards, or others' transcripts. By running them on different ports (8501 and 8502), we can apply different firewall rules and deploy them independently.</i>", quote_style))
    story.append(Spacer(1, 4))
    
    story.append(Paragraph("<b>Q: Why store audio as Base64 in MongoDB instead of saving files to a folder?</b>", body_style))
    story.append(Paragraph("<i>Answer: It makes the server completely stateless. Storing base64 MP3 strings directly in the database means any server instance can retrieve and play candidate audio instantly without sharing local filesystems, making backup and scaling simple.</i>", quote_style))
    story.append(Spacer(1, 4))
    
    story.append(Paragraph("<b>Q: Why did you choose Google Speech-to-Text?</b>", body_style))
    story.append(Paragraph("<i>Answer: Google's STT API is highly performant, requires zero local machine resources to run, handles background noise well, and has extremely low transcription latency.</i>", quote_style))
    
    # Build PDF
    doc.build(story)
    print("Enhanced PDF Successfully Generated.")

if __name__ == '__main__':
    artifacts_dir = r"C:\Users\diksa\.gemini\antigravity\brain\2ba731fb-10e4-4177-93ec-eaca06fb3377"
    pdf_path = os.path.join(artifacts_dir, "presentation_script.pdf")
    create_presentation_pdf(pdf_path)
