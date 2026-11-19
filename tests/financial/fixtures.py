"""Genera un corpus de demostración ficticio con una cifra señuelo."""
from argparse import ArgumentParser
from pathlib import Path

import pymupdf


def report(path, periods, values, *, entity="Grupo Faro", unit="millones MXN", note="", duplicate_header=False):
    with pymupdf.open() as pdf:
        pdf.new_page().insert_text((55, 55), "Documento de prueba. Grupo ficticio.")
        page = pdf.new_page()
        page.insert_textbox((55, 38, 525, 81), f"{entity} consolidado | {unit}\nMagnitud aditiva: Utilidad neta")
        rows = [
            ["Indicador", *periods],
            ["Utilidad neta", *values],
            ["Reservas", values[1], values[0]],
            ["ROE", "11.0%", "12.5%"],
        ]
        if duplicate_header:
            rows[0][-1] = rows[0][-2]
        xs, ys = [55, 245, 325, 405], [85, 115, 145, 175, 205]
        for x in xs:
            page.draw_line((x, ys[0]), (x, ys[-1]))
        for y in ys:
            page.draw_line((xs[0], y), (xs[-1], y))
        for row_index, row in enumerate(rows):
            for col_index, value in enumerate(row):
                page.insert_text((xs[col_index] + 6, ys[row_index] + 18), value)
        if note:
            page.insert_textbox((55, 224, 520, 280), note)
        pdf.save(path)


def example(folder):
    folder.mkdir()
    report(folder / "A-base.pdf", ("3T24", "9M24"), ("111.11", "280.05"))
    report(folder / "B-consultado.pdf", ("3T25", "9M25"), ("123.40", "310.10"))


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path, help="Ruta nueva para escribir los dos PDF ficticios")
    example(parser.parse_args().folder)
