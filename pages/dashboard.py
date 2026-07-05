import streamlit as st
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
import time
import pandas as pd
from datetime import timedelta


# --- เชื่อมต่อ Firebase (แก้ตรงนี้เจ้า) ---
if not firebase_admin._apps:
    # ถ้าค่าใน secrets เป็น string ที่เป็น json อยู่แล้วให้ใช้ json.loads
    # แต่ถ้าเป็น dict อยู่แล้ว ให้ใช้ st.secrets["FIREBASE"] เลย
    try:
        # ลองแบบที่ 1 (ถ้าเป็นข้อความ JSON)
        key_dict = json.loads(st.secrets["FIREBASE"])
    except:
        # ลองแบบที่ 2 (ถ้าเป็น Dictionary อยู่แล้ว)
        key_dict = st.secrets["FIREBASE"]
        
    cred = credentials.Certificate(dict(key_dict))
    firebase_admin.initialize_app(cred)

db = firestore.client()
# ต่อจากนี้คือโค้ด Dashboard ของไอด้า...


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

# 1. ดึงข้อมูลแบบเรียบง่าย (แก้เรื่อง Index แล้วเจ้า)
if calls:
    df = pd.DataFrame(calls)
        
    # จัดการเรื่องเวลาในที่เดียวจบ: บวก 7 ชม. และแสดงแค่เวลา (ชม:นาที:วินาที)
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp']) + timedelta(hours=7)
        df['timestamp'] = df['timestamp'].dt.strftime('%H:%M:%S')
 
    # --- ฟังก์ชันคลุมแถบสีเทาให้แถวที่ตอบแล้ว ---
        # --- ฟังก์ชันคุมแถบสีเทา (เฉพาะที่ตอบแล้วเท่านั้น) ---
        # --- ฟังก์ชันคุมสี: ม่วงถ้าตอบแล้ว, ชมพูถ้ายังไม่ตอบ ---
        # --- ฟังก์ชันคุมสี: ม่วงถ้าตอบแล้ว, ชมพูถ้ายังไม่ตอบ (ฉบับแก้บั๊ก None) ---
    def highlight_replied(row):
        val = row.get('reply_message')
        
        # แปลงเป็น string แล้วตัดช่องว่างออก
        val_str = str(val).strip()
        
        # เงื่อนไข: ถ้าเป็นค่าว่าง, เป็นคำว่า 'None', หรือเป็น 'nan' -> ให้มองว่ายังไม่ได้ตอบ
        if val_str == "" or val_str.lower() == "none" or val_str.lower() == "nan":
            # ชมพูพาสเทล (รอตอบ)
            return ['background-color: #fce4ec'] * len(row)
        else:
            # ม่วงพาสเทล (ตอบแล้ว)
            return ['background-color: #e1bee7'] * len(row)



    st.subheader("สถานะเตียงในวอร์ด (ล่าสุด)")
    # ใช้ style.apply เพื่อลงสี
    st.dataframe(df.style.apply(highlight_replied, axis=1), use_container_width=True)
else:
    st.info("ยังไม่มีคำขอเข้ามาในระบบ")


st.divider()
st.subheader("💬 ระบบตอบกลับคนไข้")
target_bed = st.number_input("ระบุเลขเตียง (ใส่เลข):", min_value=1, max_value=10, step=1)
reply_text = st.text_input("พิมพ์ข้อความตอบกลับ:")

if st.button("ส่งข้อความ"):
    target_bed_str = f"เตียง{target_bed}"
    
    # แก้ Query ให้ง่ายขึ้น: หาเฉพาะ bed_id แล้วเราค่อยไปกรองใน Python แทนเพื่อเลี่ยง Error Index
    pending_ref = db.collection('nurse_calls')\
                    .where("bed_id", "==", target_bed_str)\
                    .order_by("timestamp", direction=firestore.Query.DESCENDING)\
                    .limit(1)
    
    docs = list(pending_ref.stream())
    
    if docs:
        doc = docs[0]
        # ตรวจสอบซ้ำใน Python ว่าตอบไปหรือยัง
        if doc.to_dict().get("reply_message") is None:
            db.collection('nurse_calls').document(doc.id).update({"reply_message": reply_text})
            st.success(f"ตอบกลับ {target_bed_str} เรียบร้อยแล้วค่ะ!")
            st.rerun()
        else:
            st.warning(f"{target_bed_str} ได้รับการตอบกลับไปแล้วเจ้า")
    else:
        st.warning(f"ไม่พบรายการของ {target_bed_str} ค่ะ")

if st.button('🔁 อัปเดตข้อมูล'):
    st.rerun()
time.sleep(5)
st.rerun()
