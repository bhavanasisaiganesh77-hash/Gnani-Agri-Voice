import llm_service

print("Testing Gemini connection...")

try:
    provider = llm_service.get_provider()

    print("Provider:", provider.name)
    print("Configured:", provider.is_configured())

    answer = provider.generate(
        system="You are an agricultural assistant.",
        messages=[
            {
                "role": "user",
                "content": "Give one simple tip for growing paddy."
            }
        ],
        max_tokens=100
    )

    print("\nGemini response:")
    print(answer)

except Exception as e:
    print("\nGemini test failed.")
    print("Error type:", type(e).__name__)
    print("Error:", str(e))