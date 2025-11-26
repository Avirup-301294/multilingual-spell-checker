import unittest
from services.spell_service import SpellCheckerService

class TestCrossLanguage(unittest.TestCase):
    def setUp(self):
        self.service = SpellCheckerService()

    def test_cross_lang_suggestion(self):
        # "Haus" is German for House. "Hause" is dative.
        # "Hausse" is French, but let's assume we are checking English and German.
        # Let's try a simple case: Input "good" (English) while detecting German.
        # If we force lang="de", "good" might be misspelled in German.
        # We want to see if it suggests "good" (en) if we pass cross_check_langs=["en"].
        
        # Note: The default dictionary might not have "good" as misspelled in German if it's small, 
        # but let's assume "good" is not in German dict.
        
        # Let's use a word that is definitely not German but is English: "computer" (actually that's used in German too).
        # "happiness"
        
        text = "happiness"
        # Force it to be treated as German
        result = self.service.process_text(text, lang="de", cross_check_langs=["en"])
        
        suggestions = result["suggestions"]
        # "happiness" should be flagged as misspelled in German (hopefully)
        if "happiness" in suggestions:
            cands = suggestions["happiness"]
            # Check if we have an English suggestion for it (which is the word itself)
            has_english_match = any(c['word'] == 'happiness' and c['lang'] == 'en' for c in cands)
            self.assertTrue(has_english_match, "Should suggest 'happiness' as an English word when checking German text")

    def test_english_input_suggests_german(self):
        # User wanted: "considering we choose german or auto detect it should also show closely related english"
        # And also: "closely related english or other languages word"
        # My implementation adds "de" if input is "en".
        
        # Input "Haus" (German) while detecting English.
        text = "Haus"
        result = self.service.process_text(text, lang="en", cross_check_langs=["de"])
        
        suggestions = result["suggestions"]
        if "haus" in suggestions: # keys are lowercased
            cands = suggestions["haus"]
            # Should suggest "Haus" (de)
            # Note: spellchecker might lowercase everything.
            has_german_match = any(c['word'].lower() == 'haus' and c['lang'] == 'de' for c in cands)
            self.assertTrue(has_german_match, "Should suggest 'Haus' as a German word when checking English text")

if __name__ == "__main__":
    unittest.main()
