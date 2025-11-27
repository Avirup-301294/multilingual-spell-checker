import re
from typing import List, Dict, Tuple
from spellchecker import SpellChecker

# Optional dependencies
try:
    import cld3
except Exception:
    cld3 = None

try:
    from symspellpy import SymSpell, Verbosity
except Exception:
    SymSpell = None
    Verbosity = None

WORD_RE = re.compile(r"[A-Za-z']+")

class SpellCheckerService:
    def __init__(self):
        self.spell = SpellChecker()
        self.spell_engines: Dict[str, SpellChecker] = {"en": self.spell}
        
        # Pre-load common languages to avoid cold start latency
        # especially 'de' since it's used for cross-checking English
        try:
            self.spell_engines["de"] = self._create_fallback_engine("de")
        except Exception:
            pass
            
        self.sym_spell = self._initialize_symspell()

    def _initialize_symspell(self):
        sym_spell = None
        if SymSpell is not None:
            try:
                sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
                # Try to extract word-frequency data from the SpellChecker instance
                self._populate_symspell(sym_spell)
            except Exception as e:
                print(f"Failed to initialize SymSpell: {e}")
                sym_spell = None
        return sym_spell

    def _populate_symspell(self, sym_spell):
        freq_source = getattr(self.spell, "word_frequency", None)
        if freq_source is None:
            return

        items = None
        # try several common attribute names
        for attr in ("items", "items()", "_word_frequency", "_frequency", "_data", "dictionary", "words"):
            try:
                val = getattr(freq_source, attr)
                if callable(val):
                    items = val()
                else:
                    items = val
                if items:
                    break
            except Exception:
                continue

        added = 0
        if isinstance(items, dict):
            for w, c in items.items():
                try:
                    sym_spell.create_dictionary_entry(w, int(c))
                    added += 1
                except Exception:
                    continue
        elif isinstance(items, (list, tuple)):
            for w in items:
                try:
                    sym_spell.create_dictionary_entry(w, 1)
                    added += 1
                except Exception:
                    continue
        
        if added:
            print(f"SymSpell initialized with ~{added} entries")
        else:
            print("SymSpell initialized but no entries were loaded")

    def _preserve_case(self, original: str, corrected: str) -> str:
        if original.isupper():
            return corrected.upper()
        if original[0].isupper():
            return corrected.capitalize()
        return corrected

    def detect_language(self, text: str) -> Tuple[str, float]:
        if not text:
            return ("und", 0.0)
        if cld3 is None:
            return ("und", 0.0)
        try:
            res = None
            if hasattr(cld3, "get_language"):
                res = cld3.get_language(text)
            elif hasattr(cld3, "detect_language"):
                res = cld3.detect_language(text)
            if not res:
                return ("und", 0.0)
            lang = getattr(res, "language", None) or getattr(res, "language_code", None)
            prob = getattr(res, "probability", None) or getattr(res, "confidence", 0.0)
            return (lang or "und", float(prob or 0.0))
        except Exception:
            return ("und", 0.0)

    def get_engine(self, lang: str):
        engine = self.spell
        if lang and lang != "und":
            engine = self.spell_engines.get(lang)
            if engine is None:
                try:
                    engine = SpellChecker(language=lang)
                    self.spell_engines[lang] = engine
                except Exception:
                    # Fallback logic similar to original app.py
                    engine = self._create_fallback_engine(lang)
                    self.spell_engines[lang] = engine
        return engine

    def _create_fallback_engine(self, lang: str):
        try:
            engine = SpellChecker(language=None) # Empty engine
            import os
            # Assuming data directory is relative to the service file or we need to adjust path
            # For simplicity, let's assume data is in the parent directory's data folder
            # We might need to adjust this path depending on where this file is located relative to data
            base_dir = os.path.dirname(os.path.dirname(__file__))
            wl_path = os.path.join(base_dir, "data", f"{lang}_words.txt")
            
            if not os.path.exists(wl_path) and lang == "de":
                 wl_path = os.path.join(base_dir, "data", "german_words.txt")

            if os.path.exists(wl_path):
                with open(wl_path, "r", encoding="utf-8") as f:
                    words = [l.strip() for l in f.readlines() if l.strip()]
                
                wf = getattr(engine, "word_frequency", None)
                if wf is not None:
                    if hasattr(wf, "load_words"):
                        wf.load_words(words)
                    elif hasattr(wf, "add"):
                        for w in words:
                            try: wf.add(w)
                            except: pass
                    else:
                        try: engine.word_frequency.load_words(words)
                        except: pass
            return engine
        except Exception:
            return self.spell

    def process_text(self, text: str, mode: str = "balanced", lang: str = None, cross_check_langs: List[str] = None) -> Dict:
        if not text:
            return {"tokens": []}

        # Split text into tokens (words and non-words) keeping delimiters
        # This regex captures words and keeps everything else as separate tokens
        tokens_raw = re.split(r"([A-Za-z']+)", text)
        
        engine = self.get_engine(lang)
        
        # Prepare cross-check engines
        cross_engines = []
        if cross_check_langs:
            for cl in cross_check_langs:
                if cl != lang:
                    cross_engines.append((cl, self.get_engine(cl)))

        # Identify misspelled words for batch processing
        words_to_check = [t for t in tokens_raw if WORD_RE.fullmatch(t)]
        words_lower = [w.lower() for w in words_to_check]
        misspelled = set(engine.unknown(words_lower))

        processed_tokens = []

        for token in tokens_raw:
            if not token:
                continue
                
            token_data = {
                "text": token,
                "type": "text",
                "is_valid": True,
                "suggestions": []
            }

            if WORD_RE.fullmatch(token):
                token_data["type"] = "word"
                key = token.lower()
                
                if key in misspelled:
                    token_data["is_valid"] = False
                    
                    # Primary language suggestions
                    primary_candidates = []
                    # Use SymSpell for 'balanced' mode too if available, as it's much faster
                    if (mode == "fast" or mode == "balanced") and self.sym_spell is not None and Verbosity is not None:
                        try:
                            lookup = self.sym_spell.lookup(key, Verbosity.CLOSEST, max_edit_distance=2)
                            primary_candidates = [s.term for s in lookup] if lookup else []
                        except Exception:
                            primary_candidates = []

                    if not primary_candidates:
                        try:
                            cand = engine.candidates(key)
                            if cand:
                                primary_candidates = sorted(list(cand), key=lambda w: engine.word_frequency[w], reverse=True)
                            else:
                                primary_candidates = []
                        except Exception:
                            primary_candidates = []

                    # Format primary suggestions
                    formatted_suggestions = [{"word": w, "lang": lang} for w in primary_candidates[:5]]

                    # Cross-language suggestions
                    for cl_code, cl_engine in cross_engines:
                        try:
                            if key in cl_engine:
                                formatted_suggestions.append({"word": key, "lang": cl_code})
                            else:
                                cl_cands = cl_engine.candidates(key)
                                if cl_cands:
                                    sorted_cl = sorted(list(cl_cands), key=lambda w: cl_engine.word_frequency[w], reverse=True)[:3]
                                    for w in sorted_cl:
                                        if not any(fs["word"] == w and fs["lang"] == cl_code for fs in formatted_suggestions):
                                            formatted_suggestions.append({"word": w, "lang": cl_code})
                        except Exception:
                            continue
                    
                    token_data["suggestions"] = formatted_suggestions
            else:
                if token.isspace():
                    token_data["type"] = "space"
                else:
                    token_data["type"] = "punctuation"

            processed_tokens.append(token_data)

        return {"tokens": processed_tokens}
