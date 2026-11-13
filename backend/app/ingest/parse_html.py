import re

from bs4 import BeautifulSoup

# Site chrome repeats on every GSU page and drowns out the content the LLM should read
NOISE_TAGS = ["script", "style", "noscript", "nav", "header", "footer", "form", "svg", "iframe"]


def clean_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(NOISE_TAGS):
        tag.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ")).strip()
