import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
import requests

# --- เชื่อมต่อ Firebase ---
if not firebase_admin._apps:
    # ดึงกุญแจมาจาก Secrets ที่เราตั้งไว้ในหน้าเว็บ Streamlit
    key_dict = st.secrets["FIREBASE"]
    
    # ถ้าค่าเป็น Dictionary อยู่แล้วให้ใช้ได้เลย แต่ถ้าเป็น String ให้แปลงเป็น dict
    if isinstance(key_dict, str):
        key_dict = json.loads(key_dict)
        
    cred = credentials.Certificate(dict(key_dict))
    firebase_admin.initialize_app(cred)

db = firestore.client()
# บรรทัดที่ 20-21 ต้องเรียกตามกลุ่มที่ตั้งไว้ใน Secrets
TELEGRAM_TOKEN = st.secrets["TELEGRAM"]["TOKEN"]
TELEGRAM_CHAT_ID = st.secrets["TELEGRAM"]["CHAT_ID"]


# --- ฟังก์ชัน ---
def save_to_firestore(bed, name, urgency, message):
    current_time = datetime.datetime.now()
    data = {
        "bed_id": bed, 
        "patient_name": name, 
        "urgency": urgency, 
        "message": message, 
        "timestamp": current_time,
        "status": "waiting",
        "reply_message": None
    }
    db.collection('nurse_calls').add(data)

# --- หน้าจอหลัก ---
patient_db = {
    "เตียง1": "นาย หมอต้าเบี้ยว", "เตียง2": "นาย เกย์ent", "เตียง3": "นางสาว ไอด้า",
    "เตียง4": "นาย ยุก", "เตียง5": "นางสาว แคท", "เตียง6": "นาย แมว",
    "เตียง7": "นาย บูม", "เตียง8": "นาง แก้ว", "เตียง9": "นาย คำ", "เตียง10": "นาย วี"
}

st.title("NexCall - เลือกเตียง")
select_bed = st.selectbox("กรุณาเลือกเตียง:", list(patient_db.keys()))
patient_name = patient_db[select_bed]
st.info(f"ผู้ป่วย: {patient_name} ({select_bed})")

# 1. ตรวจสอบสถานะและข้อความจากพยาบาล (ดึงข้อมูลเรียลไทม์)
calls_ref = db.collection('nurse_calls').where("bed_id", "==", select_bed).order_by("timestamp", direction=firestore.Query.DESCENDING).limit(1)
last_call = next(calls_ref.stream(), None)

if last_call:
    call_data = last_call.to_dict()
    if call_data.get('reply_message'):
        st.success(f"พยาบาลตอบกลับมาว่า: {call_data['reply_message']}")
    else:
        st.info("⏳ ระบบได้รับคำขอแล้ว กำลังรอพยาบาลตรวจสอบนะคะ...")

# 2. ระบบ Triage & ส่งข้อมูล
st.subheader("ระดับความด่วน")
urgency = st.radio("เลือกความเร่งด่วน:", ["🟢 ปกติ", "🟡 กึ่งด่วน", "🔴 ฉุกเฉิน"])
option = st.radio("ความต้องการ:", ["ขอน้ำ", "ขอห้องน้ำ", "ปวดหลัง", "อื่นๆ (พิมพ์เอง)"])
message = st.text_input("ระบุเพิ่มเติม:") if option == "อื่นๆ (พิมพ์เอง)" else option

if st.button("ส่งข้อมูล"):
    full_msg = f"{urgency}\n🔔 แจ้งเตือนจาก {select_bed}\n👤 ผู้ป่วย: {patient_name}\n💬: {message}"

    # ใช้ requests.post ตรงนี้ (ตรวจสอบให้แน่ใจว่าเคาะ Tab เข้ามา 1 ครั้ง)
    requests.post(f"https://api.telegram.org/bot{st.secrets['TELEGRAM']['TOKEN']}/sendMessage", params={'chat_id': st.secrets['TELEGRAM']['CHAT_ID'], 'text': full_msg})

    save_to_firestore(select_bed, patient_name, urgency, message)
    st.success("ส่งคำขอเรียบร้อยแล้วค่ะ!")
    st.rerun()




