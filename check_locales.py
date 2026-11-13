import json
import re
from pathlib import Path

LOCALES_DIR = Path("locales")

LANGUAGES = [
    "te", "ta", "hi",
    "bn", "kn", "gu",
    "mr", "pa", "ml"
]


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def get_placeholders(value):
    if not isinstance(value, str):
        return set()

    return set(
        re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", value)
    )


def flatten(data, prefix=""):
    result = {}

    if not isinstance(data, dict):
        return result

    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key

        if isinstance(value, dict) and value:
            result.update(flatten(value, full_key))
        else:
            result[full_key] = value

    return result


def is_dynamic_message(key):
    return key == "msg" or key.startswith("msg.")


def main():
    english_path = LOCALES_DIR / "en.json"

    if not english_path.exists():
        print("ERROR: locales/en.json not found.")
        return

    try:
        english = flatten(load_json(english_path))
    except Exception as error:
        print(f"English JSON error: {error}")
        return

    # Exclude dynamic messages from normal key comparison.
    english_keys = {
        key for key in english
        if not is_dynamic_message(key)
    }

    print(f"English source: {len(english_keys)} translation keys\n")

    all_passed = True

    for language in LANGUAGES:
        path = LOCALES_DIR / f"{language}.json"

        if not path.exists():
            print(f"[MISSING FILE] {language}.json")
            all_passed = False
            continue

        try:
            translated = flatten(load_json(path))
        except Exception as error:
            print(f"[INVALID JSON] {language}.json: {error}")
            all_passed = False
            continue

        translated_keys = {
            key for key in translated
            if not is_dynamic_message(key)
        }

        missing = english_keys - translated_keys
        extra = translated_keys - english_keys

        placeholder_errors = []

        for key in sorted(english_keys & translated_keys):
            expected = get_placeholders(english[key])
            actual = get_placeholders(translated[key])

            if expected != actual:
                placeholder_errors.append(
                    (key, expected, actual)
                )

        if not missing and not extra and not placeholder_errors:
            print(f"[PASS] {language}.json")
        else:
            all_passed = False
            print(f"\n[CHECK] {language}.json")

            for key in sorted(missing):
                print(f"  Missing key: {key}")

            for key in sorted(extra):
                print(f"  Extra key: {key}")

            for key, expected, actual in placeholder_errors:
                print(f"  Placeholder mismatch: {key}")
                print(f"    Expected: {expected}")
                print(f"    Found:    {actual}")

    print("\n" + "=" * 45)

    if all_passed:
        print("SUCCESS: All locale files passed validation!")
    else:
        print("Some locale files need corrections.")

    print("=" * 45)


if __name__ == "__main__":
    main()