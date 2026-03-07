import streamlit as st
import google.generativeai as genai
import time
import re

# --- පිටුවේ සැකසුම් ---
st.set_page_config(page_title="Sinhala Natural Subtitler", page_icon="🎬", layout="centered")

st.title("🎬 Sinhala Natural Subtitle Translator")
st.markdown("ස්වභාවික කතාකරන භාෂාවෙන් (Raw/Street tone) සබ්ටයිටල් ට්‍රාන්ස්ලේට් කරමු!")

# --- API Key එක ලබාගැනීම ---
api_key = st.text_input("ඔබේ Google Gemini API Key එක මෙතන දෙන්න:", type="password")
st.markdown("[නොමිලේ API Key එකක් ගන්න මෙතනින් යන්න](https://aistudio.google.com/app/apikey)")

# --- Safety Settings (කුණුහරුප filter වීම නැවැත්වීමට) ---
safety_settings =[
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
]

# --- AI Prompt එක ---
PROMPT_INSTRUCTIONS = """
You are a professional movie subtitler. Translate the following English SRT subtitle chunk into natural, everyday spoken Sinhala.

Guidelines:
1. Keep the exact timestamps and index numbers. Do not change or remove any timing.
2. Tone: Use informal/street language (e.g., use 'උඹ', 'බං', 'තෝ', 'පලයන්', 'වරෙන්' where appropriate).
3. Raw Language: Do not censor or soften bad words or slang. Translate them with equivalent Sinhala swear words/slang used in real life.
4. Flow: The translation should sound like a real Sri Lankan person talking.
5. IMPORTANT: Output ONLY the translated SRT text. Do not add any introductory words, notes, or markdown formatting (like ```srt). Just the raw SRT text.

Here is the subtitle chunk to translate:
"""

def split_srt_into_chunks(srt_text, chunk_size=30):
    """SRT ෆයිල් එකේ පේළි 30 ගානේ chunks වලට කඩන ෆන්ක්ශන් එක"""
    # Windows/Linux line endings හදාගැනීම
    srt_text = srt_text.replace("\r\n", "\n")
    blocks = re.split(r'\n\n+', srt_text.strip())
    
    chunks =[]
    for i in range(0, len(blocks), chunk_size):
        chunk = "\n\n".join(blocks[i:i + chunk_size])
        chunks.append(chunk)
    return chunks

def clean_ai_response(text):
    """AI එක සමහර වෙලාවට එවන ```srt වගේ කෑලි අයින් කිරීම"""
    text = text.replace("```srt", "").replace("```", "").strip()
    return text

# --- File Uploader ---
uploaded_file = st.file_uploader("ඔබේ ඉංග්‍රීසි .srt ෆයිල් එක අප්ලෝඩ් කරන්න", type=["srt"])

if uploaded_file is not None and api_key:
    # ෆයිල් එක කියවීම
    content = uploaded_file.read().decode("utf-8")
    
    chunk_size = st.slider("එක් වරකට ට්‍රාන්ස්ලේට් කරන පේළි ගණන (Chunks)", min_value=10, max_value=50, value=30)
    
    if st.button("🚀 Translate කිරීම අරඹන්න"):
        genai.configure(api_key=api_key)
        # පාවිච්චි කරන මොඩල් එක
        model = genai.GenerativeModel('gemini-1.5-flash', safety_settings=safety_settings)
        
        chunks = split_srt_into_chunks(content, chunk_size=chunk_size)
        total_chunks = len(chunks)
        
        st.info(f"සම්පූර්ණ පේළි කාණ්ඩ (Chunks) ගණන: {total_chunks} ක් හමුවුණා. ට්‍රාන්ස්ලේට් වීම ආරම්භ කෙරේ...")
        
        # UI Elements for live progress
        progress_bar = st.progress(0)
        status_text = st.empty()
        eta_text = st.empty()
        
        final_translated_srt = ""
        start_time = time.time()
        
        # Chunks එකින් එක ට්‍රාන්ස්ලේට් කිරීම
        for i, chunk in enumerate(chunks):
            try:
                # ලයිව් ස්ටේටස් අප්ඩේට් කිරීම
                status_text.text(f"⏳ ට්‍රාන්ස්ලේට් වෙමින් පවතී... (Chunk {i+1}/{total_chunks})")
                
                # AI එකට යැවීම
                response = model.generate_content(PROMPT_INSTRUCTIONS + "\n\n" + chunk)
                translated_chunk = clean_ai_response(response.text)
                
                final_translated_srt += translated_chunk + "\n\n"
                
                # Progress එක සහ ETA එක හැදීම
                progress = (i + 1) / total_chunks
                progress_bar.progress(progress)
                
                elapsed_time = time.time() - start_time
                avg_time_per_chunk = elapsed_time / (i + 1)
                remaining_time = avg_time_per_chunk * (total_chunks - i - 1)
                
                eta_minutes = int(remaining_time // 60)
                eta_seconds = int(remaining_time % 60)
                eta_text.text(f"⏱️ ඉතිරි කාලය (ආසන්න වශයෙන්): විනාඩි {eta_minutes} තත්පර {eta_seconds}")
                
                # API Limit වලට අහුනොවී ඉන්න තත්පර 2ක් නවතිමු
                time.sleep(2) 
                
            except Exception as e:
                st.error(f"Chunk {i+1} හි දෝෂයක් ආවා: {e}")
                break
        
        st.success("🎉 නියමයි! ට්‍රාන්ස්ලේශන් එක සම්පූර්ණයි.")
        eta_text.empty()
        status_text.empty()
        
        # Download Button එක
        new_filename = uploaded_file.name.replace(".srt", "_sinhala.srt")
        st.download_button(
            label="⬇️ සිංහල සබ්ටයිටල් එක Download කරගන්න",
            data=final_translated_srt,
            file_name=new_filename,
            mime="text/plain"
        )
elif uploaded_file is not None and not api_key:
    st.warning("කරුණාකර API Key එක ඇතුලත් කරන්න.")
