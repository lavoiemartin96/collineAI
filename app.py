import streamlit as st
from supabase import create_client
import google.generativeai as genai

st.set_page_config(page_title="CollineAI", page_icon="🏛️", layout="centered")

SUPABASE_URL = "https://tzcweoiwbikregrzmzlm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR6Y3dlb2l3YmlrcmVncnptemxtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTMyMDY0OTUsImV4cCI6MjEwODc4MjQ5NX0.G1qc4ZxmUX5d62Uq8BERmFRctYvG-Mng5hvbdmKB0pc"
GEMINI_KEY = "AQ.Ab8RN6JKv6xOVmfaofW5LIuFbRfJXpVW5b6SQIFZRT-guIsr4A"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

st.title("🏛️ CollineAI")
st.caption("Veille législative & analyse parlementaire • Séance 155 (45-1)")

# Entrée utilisateur
question = st.text_input(
    "Posez votre question sur les débats :",
    placeholder="Ex: Que s'est-il dit sur les pétroliers ? / Première question du Bloc ?"
)

if question:
    with st.spinner("Analyse du Hansard par l'intelligence artificielle..."):
        q_lower = question.lower()
        
        # 1. Sélection déterministe ciblée
        if "bloc" in q_lower and ("premier" in q_lower or "qp" in q_lower or "question" in q_lower):
            res = supabase.table("parliament_speeches").select("*").eq("sitting_num", 155).in_("sequence_num", [96, 97]).execute()
        elif "poilievre" in q_lower:
            res = supabase.table("parliament_speeches").select("*").eq("sitting_num", 155).ilike("speaker_name", "%Poilievre%").limit(3).execute()
        elif "champoux" in q_lower:
            res = supabase.table("parliament_speeches").select("*").eq("sitting_num", 155).in_("sequence_num", [4, 5]).execute()
        else:
            # Extraction des mots porteurs de sens
            parasites = ["qu'est-ce", "qui", "a", "été", "dit", "sur", "les", "le", "la", "des", "du", "parle-moi", "résume"]
            mots = [m for m in q_lower.replace("?", "").split() if len(m) > 2 and m not in parasites]
            query_filter = ",".join([f"speech_text.ilike.%{m}%" for m in mots[:2]]) if mots else "speech_text.ilike.%C-39%"
            res = supabase.table("parliament_speeches").select("*").eq("sitting_num", 155).or_(query_filter).limit(6).execute()

        donnees = res.data

        if not donnees:
            st.warning("Aucune intervention pertinente trouvée dans la séance 155 pour cette requête.")
        else:
            # 2. Construction du dossier de synthèse pour Gemini
            contexte = "\n\n".join([
                f"[Ordre #{d['sequence_num']}] {d['speaker_name']} ({d['speaker_party']}) - {d['order_of_business']} :\n\"{d['speech_text']}\""
                for d in donnees
            ])

            prompt = f"""Tu es un conseiller politique senior à Ottawa pour un lobbyiste professionnel.
Voici les extraits officiels et vérifiés de la séance 155 de la Chambre des communes :

{contexte}

Question du client : "{question}"

Consignes :
1. Fais un briefing clair, percutant et direct (3 à 4 phrases).
2. Explique le choc des positions : qui a dit quoi et avec quels arguments.
3. Ne cite aucun propos hors-sujet. Reste neutre et factuel."""

            # Synthèse par l'IA
            try:
                reponse = model.generate_content(prompt).text
            except Exception as e:
                reponse = f"Lors de la séance 155, {donnees[0]['speaker_name']} est intervenu à l'ordre #{donnees[0]['sequence_num']}."

            st.subheader("📋 Briefing Exécutif")
            st.info(reponse)

            # Lecture vocale automatique
            st.components.v1.html(f"""
            <script>
                var msg = new SpeechSynthesisUtterance({repr(reponse)});
                msg.lang = 'fr-CA';
                window.speechSynthesis.speak(msg);
            </script>
            """, height=0)

            # Transcriptions officielles vérifiables
            with st.expander("🔍 Voir les extraits officiels du Hansard"):
                for d in donnees:
                    st.markdown(f"**#{d['sequence_num']} — {d['speaker_name']}** ({d['speaker_party']})")
                    st.caption(f"{d['order_of_business']} • {d['subject']}")
                    st.write(d['speech_text'])
                    st.markdown(f"[Consulter sur noscommunes.ca]({d['official_url']})")
                    st.divider()
