import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json

# --- เชื่อมต่อ Firebase (ใช้ค่าจาก Secrets) ---
if not firebase_admin._apps:
    key_dict = json.loads(st.secrets["FIREBASE"])
    cred = credentials.Certificate(dict(key_dict))
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- ระบบล็อกอินพยาบาล ---
if "nurse_logged_in" not in st.session_state:
    st.session_state["nurse_logged_in"] = False

if not st.session_state["nurse_logged_in"]:
    st.title("🔐 เข้าสู่ระบบสำหรับพยาบาล")
    password = st.text_input("รหัสผ่าน:", type="password")
    if st.button("เข้าสู่ระบบ"):
        if password == "Idealist49":
            st.session_state["nurse_logged_in"] = True
            st.rerun()
        else:
            st.error("รหัสผ่านไม่ถูกต้อง!")
    st.stop()

# --- Dashboard พยาบาล ---
st.title("🏥 ศูนย์บัญชาการพยาบาล - NexCall Dashboard")

# 1. ดึงข้อมูลจาก Firestore
calls_ref = db.collection('nurse_calls').order_by("timestamp", direction=firestore.Query.DESCENDING).limit(20)
calls = [doc.to_dict() for doc in calls_ref.stream()]

if calls:
    import pandas as pd
    df = pd.DataFrame(calls)
    
    # ไฮไลท์แถวที่ตอบแล้ว
    def highlight_replied(row):
        return ['background-color: #d3d3d3'] * len(row) if row['reply_message'] else [''] * len(row)

    st.subheader("สถานะเตียงในวอร์ด (ล่าสุด)")
    st.dataframe(df.style.apply(highlight_replied, axis=1), use_container_width=True)
else:
    st.info("ยังไม่มีคำขอเข้ามาในระบบเจ้า")

st.divider()
st.subheader("💬 ระบบตอบกลับคนไข้")
target_bed = st.number_input("ระบุเลขเตียง (ใส่เลข):", min_value=1, max_value=10, step=1)
reply_text = st.text_input("พิมพ์ข้อความตอบกลับ:")

if st.button("ส่งข้อความ"):
    target_bed_str = f"เตียง{target_bed}"
    
    # ค้นหาคำขอที่ยังไม่ได้ตอบของเตียงนั้น
    pending_ref = db.collection('nurse_calls')\
                    .where("bed_id", "==", target_bed_str)\
                    .where("reply_message", "==", None)\
                    .order_by("timestamp", direction=firestore.Query.DESCENDING)\
                    .limit(1)
    
    docs = list(pending_ref.stream())
    
    if docs:
        doc_id = docs[0].id
        db.collection('nurse_calls').document(doc_id).update({"reply_message": reply_text})
        st.success(f"ตอบกลับ {target_bed_str} เรียบร้อยแล้วเจ้า!")
        st.rerun()
    else:
        st.warning(f"ไม่พบรายการที่ค้างตอบของ {target_bed_str} เจ้า")

if st.button('🔁 อัปเดตข้อมูล'):
    st.rerun()

