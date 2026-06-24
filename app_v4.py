import streamlit as st
import pandas as pd
import edge_tts
import asyncio
import io

# إعدادات الصفحة
st.set_page_config(page_title="قارئ درجات الطلاب الصوتي - V5", layout="centered", page_icon="🎙️")

st.title("🎙️ تطبيق قارئ الدرجات الصوتي (النسخة V5 المعالجة للملفات)")
st.write("تمت إضافة ميزة تخطي الأسطر الفارغة وتحديد سطر العناوين لحل مشاكل تنسيق الملفات.")

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
    
    # ⚙️ إعدادات التحكم المتقدمة في أعلى القائمة الجانبية
    st.sidebar.header("⚙️ إعدادات قراءة الملف والصوت")
    
    # ميزة ذكية لتحديد سطر العناوين إذا كان هناك جدول علوي أو خلايا مدمجة
    header_row = st.sidebar.number_input(
        "📍 سطر أسماء الأعمدة في ملفك (ابدأ بـ 0):", 
        min_value=0, 
        value=0, 
        help="إذا كان لديك عنوان كبير في أول سطر بالإكسيل، غير هذا الرقم إلى 1 أو 2 حتى تظهر أسماء الأعمدة بشكل صحيح."
    )
    
    # قراءة الملف بناءً على السطر المحدد
    df = pd.read_excel(uploaded_file, header=header_row)
    
    # تنظيف البيانات: حذف الأعمدة والأسطر التي تكون فارغة تماماً
    df = df.dropna(how='all')
    
    columns = df.columns.tolist()
    
    # 👩‍💼 👨‍💼 اختيار نوع الصوت
    gender = st.sidebar.radio("👤 نوع صوت المساعد:", ["امرأة (صوت نقي)", "رجل (صوت وقور)"])
    voice_id = "ar-SA-HamedNeural" if gender == "رجل (صوت وقور)" else "ar-EG-HodaNeural"
        
    # 🏃‍♂️ التحكم في السرعة
    speed_percent = st.sidebar.slider("⏱️ سرعة النطق (%):", min_value=50, max_value=150, value=100, step=10)
    diff = speed_percent - 100
    rate_str = f"{diff:+}%" if diff != 0 else "+0%"
    
    st.sidebar.markdown("---")
    
    # تحديد عمود الأسماء وحذف الأسطر التي ليس فيها اسم طالب (لتجنب ظهور nan)
    name_col = st.sidebar.selectbox("اختر عمود أسماء الطلاب:", columns, index=0)
    df = df.dropna(subset=[name_col])
    
    remaining_cols = [col for col in columns if col != name_col and not str(col).startswith('Unnamed:')]
    
    # تقسيم تلقائي ذكي للأعمدة
    default_saai = [c for c in remaining_cols if "سعي" in str(c).lower() or "يومي" in str(c).lower()]
    default_exam = [c for c in remaining_cols if "امتحان" in str(c).lower() or "فاينل" in str(c).lower()]
    default_final = [c for c in remaining_cols if "نهائي" in str(c).lower() or "مجموع" in str(c).lower()]
    
    saai_selection = st.sidebar.multiselect("1️⃣ أعمدة السعيات (تظهر كأعمدة):", remaining_cols, default=default_saai)
    exam_selection = st.sidebar.multiselect("2️⃣ أعمدة الامتحانات (تظهر كأعمدة):", remaining_cols, default=default_exam)
    final_selection = st.sidebar.multiselect("3️⃣ أعمدة الدرجات النهائية (تظهر كأعمدة):", remaining_cols, default=default_final)
    
    if 'student_index' not in st.session_state:
        st.session_state.student_index = 0
        
    total_students = len(df)
    
    if total_students == 0:
        st.warning("لم يتم العثور على بيانات طلاب في هذا السطر. يرجى تعديل 'سطر أسماء الأعمدة' من القائمة الجانبية.")
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
                st.error(f"حدث خطأ في الاتصال.")
        
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
    st.sidebar.info(f"ℹ️ السرعة الحالية: {speed_percent}% | الصوت: {gender}")
