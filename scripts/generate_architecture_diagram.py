import os
from PIL import Image, ImageDraw, ImageFont

def draw_architecture():
    W, H = 1200, 800
    img = Image.new("RGB", (W, H), (15, 23, 42)) # Slate 900 background
    d = ImageDraw.Draw(img)

    def fnt(size, bold=False):
        font_path = "C:\\Windows\\Fonts\\arialbd.ttf" if bold else "C:\\Windows\\Fonts\\arial.ttf"
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            return ImageFont.load_default()

    # Header Box
    d.rectangle([40, 30, W-40, 90], fill=(30, 41, 59), outline=(59, 130, 246), width=2)
    d.text((W//2, 60), "MediShield AI Multi-Agent Architecture", font=fnt(24, True), fill=(255, 255, 255), anchor="mm")

    # Layer 1: Ingestion & Classification
    # Upload API
    d.rectangle([60, 130, 360, 210], fill=(30, 41, 59), outline=(59, 130, 246), width=2)
    d.text((210, 160), "Document Ingestion API", font=fnt(16, True), fill=(255, 255, 255), anchor="mm")
    d.text((210, 185), "FastAPI /cases/upload", font=fnt(13), fill=(148, 163, 184), anchor="mm")

    # Arrow 1
    d.line([(360, 170), (440, 170)], fill=(59, 130, 246), width=3)
    d.polygon([(440, 170), (430, 163), (430, 177)], fill=(59, 130, 246))

    # Classifier Agent
    d.rectangle([440, 130, 760, 210], fill=(15, 23, 42), outline=(139, 92, 246), width=2)
    d.text((600, 160), "Classifier Agent", font=fnt(16, True), fill=(167, 139, 250), anchor="mm")
    d.text((600, 185), "Groq LLaMA-3.3 70B / Vision", font=fnt(13), fill=(148, 163, 184), anchor="mm")

    # Arrow Down to Agents
    d.line([(600, 210), (600, 260)], fill=(139, 92, 246), width=3)
    d.line([(150, 260), (1050, 260)], fill=(139, 92, 246), width=3)

    # Layer 2: 4 Specialist Agents
    agents = [
        ("KYC Agent", "Identity & ELA Tamper Analysis", 60, (6, 182, 212)),
        ("Claims Agent", "CMS-1500 / CPT & ICD-10 Schema", 340, (16, 185, 129)),
        ("Policy RAG Agent", "Vector Search Gold & Silver PDFs", 620, (245, 158, 11)),
        ("Fraud Agent", "Patient History & Anomaly Score", 900, (239, 68, 68)),
    ]

    for title, desc, x, color in agents:
        d.line([(x+120, 260), (x+120, 300)], fill=color, width=3)
        d.polygon([(x+120, 300), (x+113, 290), (x+127, 290)], fill=color)
        
        d.rectangle([x, 300, x+240, 410], fill=(30, 41, 59), outline=color, width=2)
        d.text((x+120, 335), title, font=fnt(16, True), fill=(255, 255, 255), anchor="mm")
        d.text((x+120, 375), desc, font=fnt(12), fill=(148, 163, 184), anchor="mm")
        
        # Connect to Orchestrator
        d.line([(x+120, 410), (x+120, 460)], fill=color, width=3)

    d.line([(180, 460), (1020, 460)], fill=(16, 185, 129), width=3)
    d.line([(600, 460), (600, 490)], fill=(16, 185, 129), width=3)
    d.polygon([(600, 490), (593, 480), (607, 480)], fill=(16, 185, 129))

    # Layer 3: Orchestrator Agent
    d.rectangle([400, 490, 800, 580], fill=(15, 23, 42), outline=(16, 185, 129), width=3)
    d.text((600, 525), "Orchestrator Agent Node", font=fnt(18, True), fill=(52, 211, 153), anchor="mm")
    d.text((600, 555), "Synthesizes Decision: APPROVE / REJECT / ESCALATE", font=fnt(13), fill=(148, 163, 184), anchor="mm")

    # Connect to Storage & UI
    d.line([(600, 580), (600, 630)], fill=(59, 130, 246), width=3)
    d.polygon([(600, 630), (593, 620), (607, 620)], fill=(59, 130, 246))

    # Layer 4: Storage & UI
    # Database
    d.rectangle([160, 630, 520, 730], fill=(30, 41, 59), outline=(245, 158, 11), width=2)
    d.text((340, 665), "SQLite Database (WAL Mode)", font=fnt(16, True), fill=(255, 255, 255), anchor="mm")
    d.text((340, 695), "Speed Indexed Cases & Audit Log", font=fnt(13), fill=(148, 163, 184), anchor="mm")

    # Case Management Web UI
    d.rectangle([680, 630, 1040, 730], fill=(30, 41, 59), outline=(59, 130, 246), width=2)
    d.text((860, 665), "Case Management Web UI", font=fnt(16, True), fill=(255, 255, 255), anchor="mm")
    d.text((860, 695), "Single Page App & Review Queue", font=fnt(13), fill=(148, 163, 184), anchor="mm")

    # Connect DB to UI
    d.line([(520, 680), (680, 680)], fill=(59, 130, 246), width=2)

    # Save diagram
    out_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "architecture_diagram.png"))
    img.save(out_path, "PNG")
    print(f"Generated architecture diagram image: {out_path}")

if __name__ == "__main__":
    draw_architecture()
