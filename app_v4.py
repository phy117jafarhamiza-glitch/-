import streamlit as st
import pandas as pd
import edge_tts
import asyncio
import io

# إعدادات الصفحة
st.set_page_config(page_title="قارئ درجات الطلاب الصوتي - V4", layout="centered", page_icon="🎙️")

st.title("🎙️ تطبيق قارئ الدرجات الصوتي (النسخة الاحترافية V4)")
st.write("تمت ترقية محرك الصوت بالكامل لدعم اختيار صوت (رجل أو امرأة) والتحكم الدقيق في السرعة عبر زر مخصص.")

# دالة لتوليد الصوت باستخدام ميكروسوفت إيدج عبر edge-tts
async def text_to_speech_edge(text, voice, rate_str):
    communicate = edge_tts.Communicate(text, voice, rate=rate_str)
    audio_buffer = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_buffer.write(chunk["data"])
    audio_buffer.seek(0)
    return audio_buffer

# رفع ملف الإكسيل
uploaded_file = st.file_uploader("اختر ملف إكسيل (xlsx)", type=["xlsx"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    st.success("تم تحميل الملف بنجاح!")
    
    columns = df.columns.tolist()
    
    # قائمة التحكم الجانبية لخيارات الصوت المتقدمة
    st.sidebar.header("⚙️ إعدادات الصوت المتقدمة")
    
    # 👩‍💼 👨‍💼 اختيار نوع الصوت (رجل أو امرأة)
    gender = st.sidebar.radio("👤 نوع صوت المساعد:", ["امرأة (صوت نقي)", "رجل (صوت وقور)"])
    
    if gender == "رجل (صوت وقور)":
        voice_id = "ar-SA-HamedNeural"  # صوت رجل سعودي طبيعي
    else:
        voice_id = "ar-EG-HodaNeural"   # صوت امرأة مصري طبيعي ونقي
        
    # 🏃‍♂️ زر مخصص للتحكم في السرعة بدقة
    speed_percent = st.sidebar.slider("⏱️ سرعة النطق (%):", min_value=50, max_value=150, value=100, step=10)
    
    diff = speed_percent - 100
    rate_str = f"{diff:+}%" if diff != 0 else "+0%"
    
    st.sidebar.markdown("---")
    name_col = st.sidebar.selectbox("اختر عمود أسماء الطلاب:", columns, index=0)
    remaining_cols = [col for col in columns if col != name_col]
    
    # تقسيم تلقائي ذكي للأعمدة
    default_saai = [c for c in remaining_cols if "سعي" in str(c).lower() or "يومي" in str(c).lower()]
    default_exam = [c for c in remaining_cols if "امتحان" in str(c).lower() or "فاينل" in str(c).lower()]
    default_final = [c for c in remaining_cols if "نهائي" in str(c).lower() or "مجموع" in str(c).lower()]
    
    saai_selection = st.sidebar.multiselect("1️⃣ أعمدة السعيات:", remaining_cols, default=default_saai)
    exam_selection = st.sidebar.multiselect("2️⃣ أعمدة الامتحانات:", remaining_cols, default=default_exam)
    final_selection = st.sidebar.multiselect("3️⃣ أعمدة الدرجات النهائية:", remaining_cols, default=default_final)
    
    if 'student_index' not in st.session_state:
        st.session_state.student_index = 0
        
    total_students = len(df)
    
    if total_students == 0:
        st.warning("الملف فارغ.")
    else:
        if st.session_state.student_index >= total_students:
            st.session_state.student_index = total_students - 1
        if st.session_state.student_index < 0:
            st.session_state.student_index = 0
            
        current_idx = st.session_state.student_index
        row = df.iloc[current_idx]
        student_name = str(row[name_col])
        
        st.markdown(f"### 🗂️ الطالب الحالي: {current_idx + 1} من {total_students}")
        st.info(f"👤 **اسم الطالب:** {student_name}")
        
        speech_text = f"الطالب: {student_name}. "
        
        st.markdown("#### 📊 الترتيب الحالي للنطق:")
        
        def process_grades(cols_list, group_title):
            global speech_text
            if cols_list:
                st.write(f"**{group_title}:**")
                display_list = []
                for col in cols_list:
                    val = row[col]
                    if pd.isna(val):
                        val_str = "غائب"
                    else:
                        if isinstance(val, float) and val.is_integer():
                            val = int(val)
                        val_str = str(val)
                    
                    speech_text += f"{val_str}، "
                    display_list.append(f"`{col}: {val_str}`")
                st.markdown(" | ".join(display_list))
        
        process_grades(saai_selection, "🔹 درجات السعي (أولاً)")
        process_grades(exam_selection, "🔸 درجات الامتحان (ثانياً)")
        process_grades(final_selection, "✅ الدرجة النهائية (أخيراً)")
        
        with st.spinner("جاري تحضير الصوت بالصيغة المختارة..."):
            try:
                audio_data = asyncio.run(text_to_speech_edge(speech_text, voice_id, rate_str))
                st.audio(audio_data, format="audio/mp3", autoplay=True)
            except Exception as e:
                st.error(f"حدث خطأ أثناء توليد الصوت. تأكد من اتصالك بالإنترنت.")
        
        st.divider()
        
        col_prev, col_replay, col_next = st.columns(3)
        with col_prev:
            if st.button("⬅️ السابق", use_container_width=True, disabled=(current_idx == 0)):
                st.session_state.student_index -= 1
                st.rerun()
        with col_replay:
            if st.button("🔄 إعادة النطق", use_container_width=True):
                st.rerun()
        with col_next:
            if st.button("التالي ➡️", use_container_width=True, disabled=(current_idx == total_students - 1)):
                st.session_state.student_index += 1
                st.rerun()

    # التعديل هنا: تم إدخال هذين السطرين تحت نطاق الـ if الخاصة بالملف (بإضافة 4 مسافات بادئة)
    st.sidebar.markdown("---")
    st.sidebar.info(f"ℹ️ **معلومات الصوت الحالية:**\n- المحرك: Microsoft Neural\n- السرعة المحددة: {speed_percent}%\n- نوع النطق: {gender}")
