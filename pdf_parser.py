from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, BooleanObject

reader = PdfReader("example.pdf")
writer = PdfWriter()

updated_data = {
    "Naam": "John Doe"
}

page = reader.pages[0]
writer.add_page(page)

# Update form field values
writer.update_page_form_field_values(writer.pages[0], updated_data)

# Copy over AcroForm and set NeedAppearances to True
acro_form = reader.trailer["/Root"].get("/AcroForm")
if acro_form:
    acro_form.update({
        NameObject("/NeedAppearances"): BooleanObject(True)
    })
    writer._root_object.update({
        NameObject("/AcroForm"): acro_form
    })

# Save to output
with open("output.pdf", "wb") as f:
    writer.write(f)
