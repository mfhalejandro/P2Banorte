"""Backend de navegador con documentos exclusivamente sintéticos."""
from pathlib import Path
from tempfile import TemporaryDirectory

import uvicorn

from apps.api.corpus import Corpus
from apps.api.agent import LocalExtractive
from apps.api.main import create_app
from fixture_pdf import example_corpus


if __name__ == "__main__":
    with TemporaryDirectory() as temp:
        root = Path(temp)
        corpus = Corpus(example_corpus(root / "pdf"), root / "state")
        corpus.index()
        uvicorn.run(create_app(corpus, provider=LocalExtractive()), host="127.0.0.1", port=8179)
