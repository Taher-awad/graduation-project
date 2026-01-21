
import docx

doc = docx.Document("Final_EduVR_Report.md.docx")
found = False
for i, p in enumerate(doc.paragraphs):
    if "documentation/images" in p.text or ".png" in p.text:
        print(f"MATCH [{i}]: {p.text}")
        found = True

if not found:
    print("No 'documentation/images' or '.png' found in the text.")
