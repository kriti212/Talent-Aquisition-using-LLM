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
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#4f46e5'),
        alignment=1, # Center
        spaceAfter=15
    )
    
    h1_style = ParagraphStyle(
        'SecHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#1e293b'),
        spaceBefore=15,
        spaceAfter=8,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
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
    
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.white
    )
    
    table_body_style = ParagraphStyle(
        'TableBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#1e293b')
    )
    
    story = []
    
    # Title
    story.append(Paragraph("AI Talent Acquisition Platform", title_style))
    story.append(Paragraph("Presentation & Live Demo Script", ParagraphStyle('Sub', parent=title_style, fontSize=14, leading=16, textColor=colors.HexColor('#64748b'), spaceAfter=20)))
    story.append(Spacer(1, 10))
    
    # Section 1
    story.append(Paragraph("1. Introduction (The Pitch) - 2 Minutes", h1_style))
    story.append(Paragraph("<b>The Problem</b>: Traditional hiring is slow, manual resume screening is often biased, and initial technical screening takes up valuable engineering hours.", bullet_style))
    story.append(Paragraph("<b>The Solution</b>: We built an AI-powered talent acquisition platform that automates the early stages of recruitment. The platform parses resumes semantically, recommends the top 5 matching job roles using hybrid vector search, and conducts a 5-question technical screening interview.", bullet_style))
    story.append(Paragraph("<b>The New Feature (Voice Integration)</b>: To make the interview experience interactive and realistic, we integrated <b>voice support</b>. Candidates can speak their answers naturally. The system transcribes the speech to text, and evaluates the candidate's technical skills and communication clarity using an LLM.", bullet_style))
    story.append(Spacer(1, 10))
    
    # Section 2
    story.append(Paragraph("2. Live Demo Script (Step-by-Step) - 4 Minutes", h1_style))
    story.append(Paragraph("Connect your VPN and open the app at http://localhost:8501 before the presentation starts.", body_style))
    story.append(Spacer(1, 5))
    
    # Live Demo Table Data
    table_data = [
        [
            Paragraph("Step", table_header_style),
            Paragraph("Action on Screen", table_header_style),
            Paragraph("What to Say / Highlight", table_header_style)
        ],
        [
            Paragraph("<b>1. Resume Upload</b>", table_body_style),
            Paragraph("Upload a sample PDF/TXT resume.<br/>Click 'Process & Match Roles'.", table_body_style),
            Paragraph("<i>'Here, the candidate uploads their resume. Our backend extracts text, parses skills using python parsers, and matches the candidate to job roles using BERT embeddings. We use a hybrid vector reranking model to recommend the top 5 most suitable jobs.'</i>", table_body_style)
        ],
        [
            Paragraph("<b>2. Role Selection</b>", table_body_style),
            Paragraph("Select a recommended job role (e.g. Python Developer) and click 'Apply'.", table_body_style),
            Paragraph("<i>'The candidate reviews their extracted profile (name, experience, skills) and chooses which position they want to interview for. Once selected, our LLM generates a personalized first technical question based on their resume skills and target role.'</i>", table_body_style)
        ],
        [
            Paragraph("<b>3. Interactive Interview</b>", table_body_style),
            Paragraph("Read question.<br/>Click 'Start Recording', speak a 15-sec answer, click 'Stop & Transcribe', then click 'Submit Answer'.", table_body_style),
            Paragraph("<i>'Now we enter the conversational interview. The AI question is spoken aloud using Text-to-Speech. I will record my answer. The app uses Google Speech-to-Text to transcribe my voice. Notice that under the hood, to save database storage, this audio is compressed into an MP3 file and stored as a base64 string in MongoDB.'</i>", table_body_style)
        ],
        [
            Paragraph("<b>4. Complete & Evaluate</b>", table_body_style),
            Paragraph("Answer remaining questions, and submit the Preferences form.", table_body_style),
            Paragraph("<i>'At the end of the interview, the candidate fills out their salary expectations and work preference. Once submitted, our LLM grades the entire transcript, scoring both technical expertise and soft skills, and writes a detailed evaluation summary.'</i>", table_body_style)
        ],
        [
            Paragraph("<b>5. Admin Dashboard</b>", table_body_style),
            Paragraph("Navigate to '1 Admin Dashboard' in the sidebar. Select your newly created candidate.", table_body_style),
            Paragraph("<i>'Now we switch to the recruiter dashboard. Here, hiring managers get a high-level view of all applicants and average scores. By selecting our candidate, I can review the detailed AI scorecard, read their transcript, and—most importantly—listen to their recorded voice answers directly from my browser.'</i>", table_body_style)
        ]
    ]
    
    # Table Widths
    col_widths = [80, 150, 274]
    demo_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    demo_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#4f46e5')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#f8fafc'), colors.white]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
    ]))
    
    story.append(demo_table)
    story.append(Spacer(1, 15))
    
    # Section 3
    story.append(Paragraph("3. Technical Architecture Highlights - 2 Minutes", h1_style))
    story.append(Paragraph("<b>1. Google Speech-to-Text</b>: Used the `SpeechRecognition` library (`recognize_google`) to transcribe the voice recording accurately.", bullet_style))
    story.append(Paragraph("<b>2. Audio Compression (`lameenc`)</b>: Instead of storing raw WAV audio (which is very large and would quickly bloat our database), we downsample the audio to 16,000Hz mono and compress it to <b>MP3 format</b> using a pure Python LAME encoder. This reduces file size by <b>over 80%</b>.", bullet_style))
    story.append(Paragraph("<b>3. Database Storage</b>: The MP3 file is encoded as a <b>Base64 string</b> and stored inside MongoDB. In the Admin Dashboard, we decode this string back to binary so the recruiter can play the candidate's exact audio.", bullet_style))
    story.append(Paragraph("<b>4. Robust Fallback Mechanism</b>: If our network connection drops or the LLM server is unreachable, we wrote custom rotating fallback questions in `interview.py`. The app will gracefully cycle through 5 distinct professional questions instead of repeating the same question, protecting the candidate's user experience.", bullet_style))
    story.append(Spacer(1, 10))
    
    # Section 4
    story.append(Paragraph("4. Potential Questions & Answers", h1_style))
    story.append(Paragraph("<b>Q: Why use Google STT over other voice models?</b>", body_style))
    story.append(Paragraph("<i>A: Google STT is highly accurate, fast, requires no heavy local models to run on the machine, and easily integrates with standard audio formats.</i>", ParagraphStyle('Answer', parent=body_style, leftIndent=10, spaceAfter=8)))
    
    story.append(Paragraph("<b>Q: Why store audio in MongoDB instead of saving it on disk?</b>", body_style))
    story.append(Paragraph("<i>A: Storing it as a base64 string directly in the candidate document makes the application stateless and portable. The audio is bound to the candidate record, which makes database backups, migration, and scaling much simpler without managing file servers.</i>", ParagraphStyle('Answer', parent=body_style, leftIndent=10, spaceAfter=8)))
    
    story.append(Paragraph("<b>Q: How does the system evaluate communication/soft skills?</b>", body_style))
    story.append(Paragraph("<i>A: Our LLM prompt instructs the model to analyze the structure, vocabulary, and clarity of the transcript, grading communication on a scale of 0 to 100 based on professional recruiting metrics.</i>", ParagraphStyle('Answer', parent=body_style, leftIndent=10)))
    
    # Build PDF
    doc.build(story)
    print("PDF Successfully Generated.")

if __name__ == '__main__':
    # Save the PDF directly to the user's Artifacts directory
    artifacts_dir = r"C:\Users\diksa\.gemini\antigravity\brain\2ba731fb-10e4-4177-93ec-eaca06fb3377"
    pdf_path = os.path.join(artifacts_dir, "presentation_script.pdf")
    create_presentation_pdf(pdf_path)
