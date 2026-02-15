from typing import List, Dict, Any, Tuple
import re
import spacy


class DocumentFormatter:
    """
    Reconstruct text from layout blocks and generate structured hints
    for downstream extraction or LLM guidance.
    """

    EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

    PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s-]?)?\b\d{10}\b")

    AMOUNT_RE = re.compile(
        r"(?:₹|\$|€|£|INR|USD|EUR|GBP)?\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})?"
    )

    DATE_RE = re.compile(
        r"\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b"
    )

    def __init__(self, spacy_model: str = "en_core_web_sm"):
        self.nlp = spacy.load(spacy_model)

    #reconstruct text from blocks

    def blocks_to_text(self, blocks: List[Dict[str, Any]]) -> str:
        blocks_sorted = sorted(
            blocks,
            key=lambda b: (
                b.get("page", 0),
                b.get("top", 0),
                b.get("x0", 0),
            ),
        )
        return " ".join(b["text"] for b in blocks_sorted if b.get("text"))

    # extract deterministic values quickly & cheaply

    def regex_extract(self, text: str) -> Dict[str, List[str]]:
        """
        Extract deterministic values quickly & cheaply.
        """
        return {
            "emails": self.EMAIL_RE.findall(text),
            "phones": self.PHONE_RE.findall(text),
            "amounts": self.AMOUNT_RE.findall(text),
            "dates_numeric": self.DATE_RE.findall(text),
        }

    # extract linguistic entities to guide semantic extraction

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Detect linguistic entities to guide semantic extraction.
        """
        doc = self.nlp(text)

        entities = {
            "organizations": [],
            "dates": [],
            "money": [],
            "persons": [],
            "locations": [],
        }

        for ent in doc.ents:
            if ent.label_ == "ORG":
                entities["organizations"].append(ent.text)
            elif ent.label_ == "DATE":
                entities["dates"].append(ent.text)
            elif ent.label_ == "MONEY":
                entities["money"].append(ent.text)
            elif ent.label_ == "PERSON":
                entities["persons"].append(ent.text)
            elif ent.label_ in ("GPE", "LOC"):
                entities["locations"].append(ent.text)

        return entities

    # provide constrained candidates to improve LLM accuracy

    def build_llm_hints(
        self, regex_data: Dict[str, List[str]], entities: Dict[str, List[str]]
    ) -> Dict[str, List[str]]:
        """
        Provide constrained candidates to improve LLM accuracy.
        Limits prevent prompt bloat.
        """
        return {
            "emails": regex_data["emails"][:5],
            "phones": regex_data["phones"][:5],
            "amount_candidates": regex_data["amounts"][:10],
            "numeric_dates": regex_data["dates_numeric"][:10],
            "organizations": entities["organizations"][:10],
            "dates": entities["dates"][:10],
            "money_entities": entities["money"][:10],
            "persons": entities["persons"][:10],
            "locations": entities["locations"][:10],
        }

    # main entry point

    def format_document(self, blocks: List[Dict[str, Any]]) -> Tuple[str, Dict]:
        """
        Main entry point.

        Returns:
            clean_text: reconstructed text
            hints: structured candidates for LLM guidance
        """
        clean_text = self.blocks_to_text(blocks)

        regex_data = self.regex_extract(clean_text)
        entities = self.extract_entities(clean_text)

        hints = self.build_llm_hints(regex_data, entities)

        return clean_text, hints
