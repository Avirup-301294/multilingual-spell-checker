from services.spell_service import SpellCheckerService

service = SpellCheckerService()
text = "teh world"
result = service.process_text(text)
print(f"Input: {text}")
print(f"Result: {result}")

engine = service.get_engine("en")
print(f"Candidates for 'teh': {engine.candidates('teh')}")
print(f"Correction for 'teh': {engine.correction('teh')}")
print(f"Word frequency 'the': {engine.word_frequency['the']}")
print(f"Word frequency 'eh': {engine.word_frequency['eh']}")
