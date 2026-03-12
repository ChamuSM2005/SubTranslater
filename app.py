import streamlit as st
import google.generativeai as genai
import time
import re

# --- පිටුවේ සැකසුම් ---
st.set_page_config(page_title="Sinhala Natural Subtitler", page_icon="🎬", layout="wide")

st.title("🎬 Sinhala Natural Subtitle Translator")
st.markdown("ස්වභාවික කතාකරන භාෂාවෙන් (Raw/Street tone) සබ්ටයිටල් ට්‍රාන්ස්ලේට් කරමු!")

# --- API Key ලබාගැනීම ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error("API Key එක සර්වර් එකේ සේව් කරලා නෑ! කරුණාකර Streamlit Secrets වල GEMINI_API_KEY එක ඇතුලත් කරන්න.")
    st.stop()

safety_settings =[
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
]

PROMPT_INSTRUCTIONS = """
You are a professional movie subtitler. Translate the following English SRT subtitle chunk into natural, everyday spoken Sinhala.

Guidelines:
1. Keep the exact timestamps and index numbers. Do not change or remove any timing.
2. Tone & Context: Adapt the words dynamically based on the relationship and emotion of the characters.
   - Polite/Respectful: Use 'ඔයා', 'එන්න', 'යන්න' (for strangers, formal talk, or romance)
   - Casual/Friendly: Use 'උඹ', 'මචං', 'බං', 'වරෙන්', 'පලයන්' (for friends)
   - Angry/Aggressive: Use 'තෝ', 'මූ' (for enemies or anger)
3. Raw Language & Profanity: Do NOT censor, soften, or skip any bad words, slang, or profanity. Translate English swear words directly into extreme, real-life Sinhala swear words (e.g., 'හුත්තා', 'හුකහන්', 'පකයා', 'වේසි', 'කැරියා'). Do not hold back; adapt to the exact intensity of the English word.
4. Flow: The translation must sound 100% natural, like a real Sri Lankan speaking on the street, not a dictionary.
5. IMPORTANT: Output ONLY the translated SRT text. Do not add any introductory words, notes, or markdown formatting (like ```srt). Just the raw SRT text.

Here is the subtitle chunk to translate:
"""

def split_srt_into_chunks(srt_text, chunk_size=30):
    srt_text = srt_text.replace("\r\n", "\n")
    blocks = re.split(r'\n\n+', srt_text.strip())
    chunks =[]
    for i in range(0, len(blocks), chunk_size):
        chunk = "\n\n".join(blocks[i:i + chunk_size])
        chunks.append(chunk)
    return chunks

def clean_ai_response(text):
    text = text.replace("```srt", "").replace("```", "").strip()
    return text

# --- Session State (මතකය) සකස් කිරීම ---
if 'translated_chunks' not in st.session_state:
    st.session_state.translated_chunks =[]
if 'current_chunk_index' not in st.session_state:
    st.session_state.current_chunk_index = 0
if 'current_file_name' not in st.session_state:
    st.session_state.current_file_name = ""

# --- File Uploader ---
uploaded_file = st.file_uploader("ඔබේ ඉංග්‍රීසි .srt ෆයිල් එක අප්ලෝඩ් කරන්න", type=["srt"])

if uploaded_file is not None:
    # අලුත් ෆයිල් එකක් දැම්මොත් මතකය (Progress එක) මකා දැමීම
    if st.session_state.current_file_name != uploaded_file.name:
        st.session_state.translated_chunks =[]
        st.session_state.current_chunk_index = 0
        st.session_state.current_file_name = uploaded_file.name

    content = uploaded_file.read().decode("utf-8")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### ⚙️ Settings & Progress")
        
        # ට්‍රාන්ස්ලේට් වෙන්න පටන් අරන් නම් Slider එක අක්‍රිය (Lock) කිරීම
        is_translating_started = st.session_state.current_chunk_index > 0
        chunk_size = st.slider("එක් වරකට ට්‍රාන්ස්ලේට් කරන පේළි ගණන (Chunks)", min_value=10, max_value=50, value=30, disabled=is_translating_started)
        
        chunks = split_srt_into_chunks(content, chunk_size=chunk_size)
        total_chunks = len(chunks)
        
        st.info(f"සම්පූර්ණ පේළි කාණ්ඩ (Chunks) ගණන: {total_chunks} යි. දැනට අවසන් කර ඇති ගණන: {st.session_state.current_chunk_index}")
        
        # Buttons දෙක එක පෙළට පෙන්වීමට
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            button_label = "🚀 ට්‍රාන්ස්ලේට් කිරීම අරඹන්න" if st.session_state.current_chunk_index == 0 else "▶️ නැවතුනු තැනින් අරඹන්න"
            start_btn = st.button(button_label, use_container_width=True)
        with btn_col2:
            reset_btn = st.button("🔄 නැවත මුල සිට අරඹන්න", use_container_width=True)
            if reset_btn:
                st.session_state.translated_chunks =[]
                st.session_state.current_chunk_index = 0
                st.rerun() # පිටුව Refresh කිරීම
                
        info_text = st.empty()
        progress_bar = st.empty()
        status_text = st.empty()
        eta_text = st.empty()
        download_placeholder = st.empty()

    with col2:
        st.markdown("### 👁️ Live Preview (සිංහල සබ්ටයිටල්)")
        preview_placeholder = st.empty()
        # කලින් කරපු ටික තියෙනවා නම් ඒක මුලින්ම පෙන්නනවා
        initial_preview = "\n\n".join(st.session_state.translated_chunks) if st.session_state.translated_chunks else "ඔබේ සබ්ටයිටල් ට්‍රාන්ස්ලේට් වීමට පටන් ගත් පසු මෙහි දිස්වනු ඇත..."
        preview_placeholder.text_area("Live Translation:", value=initial_preview, height=500, disabled=True)
    
    if start_btn:
        if st.session_state.current_chunk_index >= total_chunks:
            info_text.success("🎉 ට්‍රාන්ස්ලේශන් එක දැනටමත් සම්පූර්ණ වී ඇත! කරුණාකර පහළින් Download කරගන්න.")
        else:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash', safety_settings=safety_settings)
            
            info_text.info("ට්‍රාන්ස්ලේට් වීම සිදුවෙමින් පවතී...")
            
            start_time = time.time()
            is_completed_successfully = False
            
            # පටන් ගන්නේ නැවතුනු තැන ඉඳලා (current_chunk_index)
            for i in range(st.session_state.current_chunk_index, total_chunks):
                chunk = chunks[i]
                success = False
                
                # --- Auto-Retry Mechanism ---
                for attempt in range(3):
                    try:
                        if attempt > 0:
                            status_text.warning(f"⏳ නැවත උත්සාහ කරයි... (Chunk {i+1}/{total_chunks}) [Attempt {attempt+1}/3]")
                        else:
                            status_text.text(f"⏳ ට්‍රාන්ස්ලේට් වෙමින් පවතී... (Chunk {i+1}/{total_chunks})")
                        
                        response = model.generate_content(PROMPT_INSTRUCTIONS + "\n\n" + chunk)
                        translated_chunk = clean_ai_response(response.text)
                        
                        # සාර්ථක වුණොත් මතකයට (Session State) එකතු කිරීම
                        st.session_state.translated_chunks.append(translated_chunk)
                        st.session_state.current_chunk_index = i + 1
                        
                        # Live Preview එක Update කිරීම
                        current_preview = "\n\n".join(st.session_state.translated_chunks)
                        preview_placeholder.text_area("Live Translation:", value=current_preview, height=500, disabled=True)
                        
                        # Progress එක Update කිරීම
                        progress = st.session_state.current_chunk_index / total_chunks
                        progress_bar.progress(progress)
                        
                        # ETA ගණනය කිරීම (මේ වන විට ගත වූ කෑලි ගණනට අනුව)
                        chunks_done_this_run = i - st.session_state.current_chunk_index + 1
                        elapsed_time = time.time() - start_time
                        avg_time_per_chunk = elapsed_time / chunks_done_this_run if chunks_done_this_run > 0 else 0
                        remaining_time = avg_time_per_chunk * (total_chunks - i - 1)
                        
                        eta_minutes = int(remaining_time // 60)
                        eta_seconds = int(remaining_time % 60)
                        eta_text.text(f"⏱️ ඉතිරි කාලය (ආසන්න වශයෙන්): විනාඩි {eta_minutes} තත්පර {eta_seconds}")
                        
                        time.sleep(5) # API Rate Limit එකට අහු නොවී ඉන්න
                        success = True
                        break
                        
                    except Exception as e:
                        error_msg = str(e)
                        if "429" in error_msg or "Quota" in error_msg:
                            status_text.error(f"⚠️ API සීමාව පිරී ඇත (429 Error). තත්පර 20කින් නැවත උත්සාහ කරයි...")
                            time.sleep(20)
                        else:
                            st.error(f"Chunk {i+1} හි දෝෂයක් ආවා: {e}")
                            break
                
                if not success:
                    st.error(f"❌ Chunk {i+1} ට්‍රාන්ස්ලේට් කිරීමට නොහැකි විය. ක්‍රියාවලිය මෙතනින් නවත්වනවා.")
                    break
                
                if i + 1 == total_chunks:
                    is_completed_successfully = True

            eta_text.empty()
            status_text.empty()
            
            # අවසාන සබ්ටයිටල් ෆයිල් එක හැදීම
            final_translated_srt = "\n\n".join(st.session_state.translated_chunks)
            
            if final_translated_srt.strip() != "":
                if st.session_state.current_chunk_index == total_chunks:
                    info_text.success("🎉 නියමයි! ට්‍රාන්ස්ලේශන් එක සම්පූර්ණයි.")
                else:
                    info_text.warning("⚠️ ට්‍රාන්ස්ලේශන් එක මගදී නැවතුණා. කරුණාකර 'නැවතුනු තැනින් අරඹන්න' බටන් එක ඔබන්න. නැතහොත් මෙතෙක් කර ඇති ප්‍රමාණය පහළින් Download කරගත හැක.")
                    
                new_filename = uploaded_file.name.replace(".srt", "_sinhala.srt")
                download_placeholder.download_button(
                    label="⬇️ සිංහල සබ්ටයිටල් එක Download කරගන්න",
                    data=final_translated_srt,
                    file_name=new_filename,
                    mime="text/plain"
                )

# පිටුව Load වෙද්දිම Download button එක පෙන්වීම (කලින් කරපු ටිකක් මතකයේ තියෙනවා නම්)
elif 'translated_chunks' in st.session_state and len(st.session_state.translated_chunks) > 0 and 'current_file_name' in st.session_state:
     # මෙය අදාල වන්නේ යූසර් ෆයිල් එක ඉවත් කරත් මතකයේ සබ්ටයිටල් එක තියෙන අවස්ථා වලටයි.
     pass
