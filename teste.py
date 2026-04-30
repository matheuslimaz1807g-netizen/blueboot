from google import genai

client_ia = genai.Client(api_key="AQ.Ab8RN6J3ih_28QnabMGXDYETyFaGtSErwNjyHipqhd3xKJl2pQ")

def teste_ia():
    resposta = client_ia.models.generate_content(
        model="gemini-2.5-flash",
        contents="Quanto é 4+4?"
    )
    print(resposta.text)

if __name__ == "__main__":
    teste_ia()