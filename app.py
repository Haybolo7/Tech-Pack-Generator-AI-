import os
import io
import gradio as gr
import spaces 
from PIL import Image
from huggingface_hub import InferenceClient
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle

# --- AUTHENTICATION & CLIENT ---
hf_token = os.getenv("HF_TOKEN")
client = InferenceClient("black-forest-labs/FLUX.1-schnell", token=hf_token)

# --- DETERMINISTIC TECHNICAL DATA ---
# These datasets replicate the precise tabular format seen in industry tech packs
POM_GRADED_SPEC_TABLE = [
    ["Pos", "Point of measurement", "S (cm)", "M (cm)", "L (cm)", "XL (cm)", "XXL (cm)"],
    ["A", "Body length (hsp->hem)", "67.0", "68.5", "69.0", "70.5", "72.0"],
    ["B", "Chest (ah->ah)", "50.0", "52.0", "54.0", "56.0", "58.0"],
    ["C", "Shoulder (across joints)", "44.5", "45.5", "46.5", "47.5", "48.5"],
    ["D", "Armhole (depth)", "21.0", "22.0", "23.0", "24.0", "25.0"],
    ["E", "Sleeve length (sp->sleeve)", "66.0", "67.0", "68.0", "69.0", "70.0"],
    ["F", "pocket length", "12.5", "12.5", "13.0", "13.0", "14.0"],
    ["G", "pocket width", "12.0", "12.0", "12.0", "12.5", "13.5"],
]

BOM_TABLE_DATA = [
    ["Material Component", "Detail / Specs", "Supplier", "Note"],
    ["Main Fabric", "Jersey, 100% Combed Cotton, 180 GSM", "Graph Tick", "Stock"],
    ["Rib Fabric", "1x1 Rib knit (Collar/Cuffs)", "Graph Tick", "DTM"],
    ["Threads", "Polyester, Tex 40", "TBD", "DTM"],
    ["Buttons", "Snap button, Gold Finish", "Graph Tick", "Front Placket"],
]

CONSTRUCTION_DETAILS = {
    "Labels": "Main label sewing inside yoke 2.5 cm below neck seam.",
    "Sewing": "Twin needle stitch on bottom hem and sleeve hem. Tape reinforcement across back neck.",
    "Packing": "Fold according to standards. Polybag individually. 12 pcs per carton."
}

# --- PDF GENERATION ENGINE ---
def create_pdf_tech_pack(front_sketch_pil, back_sketch_pil, style_name, g_type, prompt_text, filename="tech_pack.pdf"):
    # Convert PIL to Bytes for ReportLab
    img_b_f, img_b_b = io.BytesIO(), io.BytesIO()
    front_sketch_pil.save(img_b_f, format='PNG')
    back_sketch_pil.save(img_b_b, format='PNG')
    img_b_f.seek(0), img_b_b.seek(0)
    
    doc = SimpleDocTemplate(filename, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()

    # --- RECTIFICATION: REGISTER CUSTOM STYLES ---
    if 'Headline' not in styles:
        styles.add(ParagraphStyle(name='Headline', parent=styles['Heading1'], fontSize=14, alignment=1, textColor=colors.white))
    if 'SectionHeader' not in styles:
        styles.add(ParagraphStyle(name='SectionHeader', parent=styles['Heading1'], fontSize=12, textColor=colors.black, spaceAfter=10))

    story = []

    # 1. Header Table (Mimics image_7 header)
    header_data = [
        [Paragraph("<b>TECHNICAL PACKAGE</b>", styles['Headline']), "", f"Garment: {g_type.upper()}"],
        ["Style Name:", style_name, ""],
        ["Style Number:", "W-2026-AUTO", "Supplier: AI Tech Studio"],
    ]
    header_table = Table(header_data, colWidths=[150, 250, 140])
    header_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('BACKGROUND', (0,0), (0,0), colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 20))
    
    # 2. Sketches Section
    story.append(Paragraph("<b>SECTION 1: TECHNICAL DESIGN SKETCHES</b>", styles['SectionHeader']))
    sketch_table = Table([
        [RLImage(img_b_f, width=250, height=250), RLImage(img_b_b, width=250, height=250)],
        [Paragraph("FRONT VIEW", styles['Normal']), Paragraph("BACK VIEW", styles['Normal'])]
    ])
    sketch_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    story.append(sketch_table)
    story.append(Spacer(1, 30))
    
    # 3. POM Spec Sheet (Exactly matching user image)
    story.append(Paragraph("<b>SECTION 2: GRADED SPECIFICATION SHEET (POM)</b>", styles['SectionHeader']))
    spec_table = Table(POM_GRADED_SPEC_TABLE, colWidths=[40, 220, 50, 50, 50, 50, 50])
    spec_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('BACKGROUND', (3,1), (3,-1), colors.yellow), # Highlight M size
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('ALIGN', (1,1), (1,-1), 'LEFT'),
    ]))
    story.append(spec_table)
    story.append(Spacer(1, 30))

    # 4. BOM Section
    story.append(Paragraph("<b>SECTION 3: BILL OF MATERIALS (BOM)</b>", styles['SectionHeader']))
    bom_table = Table(BOM_TABLE_DATA, colWidths=[130, 180, 100, 100])
    bom_table.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 1, colors.black), ('BACKGROUND', (0,0), (-1,0), colors.lightgrey)]))
    story.append(bom_table)

    doc.build(story)
    return filename

# --- GRADIO INTERFACE ---
with gr.Blocks() as demo:
    gr.Markdown("# 👔 AI Tech-Pack Studio (Multi-Page PDF Generator)")
    
    with gr.Row():
        with gr.Column():
            with gr.Row():
                img_front = gr.Image(label="Front Photo", type="filepath")
                img_back = gr.Image(label="Back Photo", type="filepath")
            style_name = gr.Textbox(label="Style Name", value="G-STUDIO-V1")
            g_type = gr.Dropdown(["T-Shirt", "Shirt", "Hoodie", "Jacket"], value="T-Shirt", label="Garment Type")
            prompt = gr.Textbox(label="Technical Details", value="Slim fit, contrast zipper, ribbed cuffs")
            submit_btn = gr.Button("🚀 Generate Full Tech Pack", variant="primary")
        
        with gr.Column():
            output_file = gr.File(label="Download PDF Tech Pack")
            status = gr.Textbox(label="Status", interactive=False)

    @spaces.GPU(duration=180)
    def process(f_in, b_in, s_name, gt, u_prompt):
        if not f_in or not b_in: return None, "❌ Upload both images."
        
        try:
            # Generate sketches via API
            style_desc = "Technical flat sketch, black/white vector, clean lines, white background, no model."
            f_sketch = client.text_to_image(f"Front view: {gt}, {u_prompt}, {style_desc}")
            b_sketch = client.text_to_image(f"Back view: {gt}, {u_prompt}, {style_desc}")

            # Create PDF on CPU
            fname = f"{s_name.replace(' ', '_').lower()}_techpack.pdf"
            pdf_path = create_pdf_tech_pack(f_sketch, b_sketch, s_name, gt, u_prompt, fname)
            return pdf_path, "✅ Tech Pack Generated Successfully."
        except Exception as e:
            return None, f"❌ Error: {str(e)}"

    submit_btn.click(process, [img_front, img_back, style_name, g_type, prompt], [output_file, status])

# Launch with theme here to avoid Gradio 6.0 warnings
demo.launch(theme=gr.themes.Soft())
