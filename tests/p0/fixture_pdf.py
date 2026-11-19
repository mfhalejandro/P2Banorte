"""Corpus ficticio con páginas distinguibles para pruebas locales."""
import pymupdf


def write_pdf(path, pages):
    with pymupdf.open() as pdf:
        for number, text in enumerate(pages, 1):
            page = pdf.new_page(width=400, height=520)
            page.insert_text((35, 55), f"Página {number}", fontsize=20)
            page.insert_textbox((35, 90, 370, 440), text, fontsize=13)
        pdf.save(path)


def example_corpus(folder):
    folder.mkdir()
    write_pdf(folder / "ensayo.pdf", [
        "Informe de prueba. Presentación institucional.",
        "La reserva de crédito Faro asciende a 731 millones de pesos.",
        "Calendario de asambleas y cierre anual.",
    ])
    return folder
