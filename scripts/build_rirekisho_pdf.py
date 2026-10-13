import html
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import urllib.request
from io import BytesIO
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from pypdf import PdfReader, PdfWriter
from pypdf._font import Font
from pypdf.generic import ArrayObject, BooleanObject, NameObject, NumberObject, TextStringObject
from reportlab.lib.colors import black
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "site/rirekisho.html"
OUTPUT = ROOT / "site/rirekisho-fillable.pdf"
CHROME = shutil.which("google-chrome") or shutil.which("chromium") or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
FONT_URL = "https://raw.githubusercontent.com/google/fonts/295d98a7a0c17c68f1341eaeea354e7960ea70d3/ofl/notosansjp/NotoSansJP%5Bwght%5D.ttf"
FONT_SHA256 = "c2f3b4d463500a2ddcd3849cded1fceeb9fd6d1c32e6cbecd568453ba50fc68f"


def run_chrome(*args):
    return subprocess.run(
        [CHROME, "--headless", "--disable-gpu", "--no-sandbox", *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def make_source():
    source = SOURCE.read_text()
    source = source.replace('src="headshot-rirekisho.jpg"', f'src="{(ROOT / "site/headshot-rirekisho.jpg").as_uri()}"')
    rects = """<script>
      const rects = [...document.querySelectorAll('[data-edit], #age')].map((field) => {
        const bounds = field.getBoundingClientRect();
        const sheet = field.closest('.sheet').getBoundingClientRect();
        return {
          id: field.dataset.edit || 'age',
          page: field.closest('.sheet').classList.contains('sheet-one') ? 0 : 1,
          x: bounds.x - sheet.x,
          y: bounds.y - sheet.y,
          w: bounds.width,
          h: bounds.height
        };
      });
      document.body.dataset.rects = JSON.stringify(rects);
    </script></body>"""
    return source.replace("</body>", rects)


def get_rects(dom):
    match = re.search(r'data-rects="([^"]+)"', dom)
    if not match:
        raise ValueError("Could not read field positions from Chrome")
    return json.loads(html.unescape(match.group(1)))


def make_fields(path, rects, width, height):
    scale = width / (210 / 25.4 * 96)
    pdf = canvas.Canvas(str(path), pagesize=(width, height))
    for page in range(2):
        for rect in rects:
            if rect["page"] != page:
                continue
            x, y, w, h = (rect[key] for key in ("x", "y", "w", "h"))
            if rect["id"] == "age":
                w = 19
            elif rect["id"] == "addressKana":
                w = 380
            elif rect["id"] == "postal":
                w = 70
            elif rect["id"] in ("motivation", "preferences"):
                x, y, w, h = x + 9, y + 8, w - 18, h - 16
            field = {
                "name": rect["id"],
                "tooltip": rect["id"],
                "x": x * scale,
                "y": height - (y + h) * scale,
                "width": w * scale,
                "height": h * scale,
                "borderWidth": 0,
                "fillColor": None,
                "textColor": black,
                "fontName": "Helvetica",
                "fontSize": 9 if rect["id"] in ("motivation", "preferences") else 10,
                "value": "",
                "forceBorder": False,
            }
            if rect["id"] in ("address", "motivation", "preferences"):
                field["fieldFlags"] = "multiline"
            pdf.acroForm.textfield(**field)
        pdf.showPage()
    pdf.save()


def add_japanese_font(writer):
    data = urllib.request.urlopen(FONT_URL, timeout=30).read()
    if hashlib.sha256(data).hexdigest() != FONT_SHA256:
        raise ValueError("The Noto Sans JP font differs from the pinned version")
    font = TTFont(BytesIO(data))
    instantiateVariableFont(font, {"wght": 400}, inplace=True)
    static = BytesIO()
    font.save(static)
    static.seek(0)
    resource = Font.from_truetype_font_file(static).as_font_resource()
    descendant = resource["/DescendantFonts"][0]
    descriptor = descendant["/FontDescriptor"]
    descriptor[NameObject("/FontFile2")] = writer._add_object(descriptor["/FontFile2"])
    descendant[NameObject("/FontDescriptor")] = writer._add_object(descriptor)
    resource[NameObject("/DescendantFonts")] = ArrayObject([writer._add_object(descendant)])
    resource[NameObject("/ToUnicode")] = writer._add_object(resource["/ToUnicode"])
    acroform = writer.root_object["/AcroForm"].get_object()
    acroform["/DR"]["/Font"][NameObject("/FJ")] = writer._add_object(resource)
    for page in writer.pages:
        for reference in page["/Annots"]:
            field = reference.get_object()
            size = 9 if field["/T"] in ("motivation", "preferences") else 10
            field[NameObject("/DA")] = TextStringObject(f"/FJ {size} Tf 0 g")


def build():
    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory)
        source = temp / "rirekisho.html"
        background = temp / "background.pdf"
        fields = temp / "fields.pdf"
        source.write_text(make_source())
        url = source.as_uri()
        run_chrome("--no-pdf-header-footer", f"--print-to-pdf={background}", url)
        rects = get_rects(run_chrome("--dump-dom", url))
        pages = PdfReader(background)
        width, height = (float(value) for value in pages.pages[0].mediabox.upper_right)
        make_fields(fields, rects, width, height)
        writer = PdfWriter()
        writer.clone_document_from_reader(PdfReader(fields))
        for index in range(2):
            writer.pages[index].merge_page(pages.pages[index])
        add_japanese_font(writer)
        acroform = writer.root_object["/AcroForm"].get_object()
        acroform[NameObject("/NeedAppearances")] = BooleanObject(False)
        date = writer.get_fields()["date"]
        date[NameObject("/Q")] = NumberObject(2)
        writer.add_metadata({"/Title": "履歴書 | Matthew Trost", "/Author": "Matthew Trost"})
        with OUTPUT.open("wb") as output:
            writer.write(output)
        if set(PdfReader(OUTPUT).get_fields()) != {rect["id"] for rect in rects}:
            raise ValueError("PDF form fields do not match the webpage")


if __name__ == "__main__":
    build()
