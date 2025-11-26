from services.spell_service import SpellCheckerService

service = SpellCheckerService()
text = "Guten Tag" # Correct
text_typo = "Guten Tagg" # Typo

print("--- Testing German ---")
# Force load German engine
engine = service.get_engine("de")
print(f"Engine loaded: {engine}")

result = service.process_text(text, lang="de")
print(f"Correct input: {result}")

result_typo = service.process_text(text_typo, lang="de")
print(f"Typo input: {result_typo}")

# Check if 'Tagg' is in unknown
print(f"Is 'Tagg' unknown? {'tagg' in engine.unknown(['tagg'])}")
