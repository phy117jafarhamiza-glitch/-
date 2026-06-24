import streamlit as st
import pandas as pd
import edge_tts
import asyncio
import io

# إعدادات الصفحة
st.set_page_config(page_title="قارئ درجات الطلاب الصوتي - V6.1", layout="centered", page_icon="🎙️")

st.title("🎙️ تطبيق قارئ الدرجات الصوتي (النسخة V6.1 الذكية)")
st.write("تم تحديث الكود لإصلاح مشكلة صوت المساعد النسائي وتأكيد عمله بنجاح.")

# دالة لتوليد الصوت باستخدام ميكروسوفت إيدج
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
    # قراءة الملف بدون عناوين أولاً لتحليله ذكياً واكتشاف العناوين المدمجة
    df_raw = pd.read_excel(uploaded_file, header=None)
    
    # البحث عن السطر الذي يحتوي على الكلمات المفتاحية للدرجات
    keywords = ['سعي', 'امتحان', 'نهائي', 'يومي', 'فاينل', 'مجموع', 'درجة']
    subheader_idx = None
    for idx, row in df_raw.head(5).iterrows():
        if any(any(kw in str(cell).lower() for kw in keywords) for cell in row if pd.notna(cell)):
            subheader_idx = idx
            break
    
    # بناء أسماء الأعمدة ذكياً عبر دمج اسم المادة مع نوع الدرجة
    if subheader_idx is not None and subheader_idx > 0:
        main_header = df_raw.iloc[subheader_idx - 1].ffill().fillna('').astype(str)
        sub_header = df_raw.iloc[subheader_idx].fillna('').astype(str)
        
        new_columns = []
        for m, s in zip(main_header, sub_header):
            m_clean = m.strip()
            s_clean = s.strip()
            
            if 'اسم' in m_clean.lower() or m_clean == 'الاسم':
                new_columns.append("الاسم")
            elif m_clean == s_clean or s_clean == '':
                new_columns.append(m_clean)
            elif m_clean == '':
                new_columns.append(s_clean)
            else:
                new_columns.append(f"{m_clean} - {s_clean}")
        
        # قطع البيانات الحقيقية للطلاب من بعد سطر العناوين الفرعية
        df = df_raw.iloc[subheader_idx + 1:].copy()
        df.columns = new_columns
    else:
        df = pd.read_excel(uploaded_file, header=0)
        
    # تنظيف البيانات من الأسطر الفارغة تماماً
    df = df.dropna(how='all')
    columns = df.columns.tolist()
    
    # واجهة التحكم الجانبية لخيارات الصوت
    st.sidebar.header("⚙️ إعدادات الصوت والتحكم")
    gender = st.sidebar.radio("👤 نوع صوت المساعد:", ["امرأة (صوت نقي)", "رجل (صوت وقور)"])
    
    # تعديل محرك الصوت هنا لضمان عمل صوت المرأة (Salma)
    voice_id = "ar-SA-HamedNeural" if gender == "رجل (صوت وقور)" else "ar-EG-SalmaNeural"
    
    speed_percent = st.sidebar.slider("⏱️ سرعة النطق (%):", min_value=50, max_value=150, value=100, step=10)
    diff = speed_percent - 100
    rate_str = f"{diff:+}%" if diff != 0 else "+0%"
    
    st.sidebar.markdown("---")
    
    # التحديد التلقائي الذكي لعمود الأسماء
    if "الاسم" in columns:
        name_idx = columns.index("الاسم")
    else:
        name_idx = 0
        
    name_col = st.sidebar.selectbox("اختر عمود أسماء الطلاب:", columns, index=name_idx)
    df = df.dropna(subset=[name_col])
    
    remaining_cols = [col for col in columns if col != name_col]
    
    # تقسيم تلقائي ذكي جداً بناءً على المسميات المدمجة الجديدة
    default_saai = [c for c in remaining_cols if "سعي" in str(c) or "يومي" in str(c)]
    default_exam = [c for c in remaining_cols if "امتحان" in str(c) or "فاينل" in str(c)]
    default_final = [c for c in remaining_cols if "نهائي" in str(c) or "مجموع" in str(c)]
    
    saai_selection = st.sidebar.multiselect("1️⃣ أعمدة السعيات المكتشفة:", remaining_cols, default=default_saai)
    exam_selection = st.sidebar.multiselect("2️⃣ أعمدة الامتحانات المكتشفة:", remaining_cols, default=default_exam)
    final_selection = st.sidebar.multiselect("3️⃣ أعمدة الدرجات النهائية المكتشفة:", remaining_cols, default=default_final)
    
    if 'student_index' not in st.session_state:
        st.session_state.student_index = 0
        
    total_students = len(df)
    
    if total_students == 0:
        st.warning("لم يتم العثور على أسطر بيانات طلاب صالحة.")
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
        
        with st.spinner("جاري تحضير الصوت..."):
            try:
                audio_data = asyncio.run(text_to_speech_edge(speech_text, voice_id, rate_str))
                st.audio(audio_data, format="audio/mp3", autoplay=True)
            except Exception as e:
                st.error("حدث خطأ أثناء توليد الصوت، يرجى التحقق من الإنترنت.")
        
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

    st.sidebar.markdown("---")
    st.sidebar.info(f"ℹ️ السرعة: {speed_percent}% | الصوت المختار: {gender}")
