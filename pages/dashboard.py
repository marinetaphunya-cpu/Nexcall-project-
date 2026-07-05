import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
import time
import pandas as pd
from datetime import timedelta
import base64

# --- ฟังก์ชันเล่นเสียง ---
# เปลี่ยนฟังก์ชันเดิมเป็นอันนี้เจ้า
def play_alert_sound():
    js_code = """
    <script>
        // ขออนุญาตส่งการแจ้งเตือนก่อน
        if (Notification.permission !== "granted") {
            Notification.requestPermission();
        }
        
        // ส่งการแจ้งเตือนไปที่หน้าจอ iPad
        new Notification("แจ้งเตือน NexCall!", {
            body: "มีคนไข้กดเรียกพยาบาลค่ะ!",
            icon: "https://cdn-icons-png.flaticon.com/512/3063/3063183.png"
        });
    </script>
    """
    st.components.v1.html(js_code, height=0)




# --- เชื่อมต่อ Firebase ---
if not firebase_admin._apps:
    try:
        key_dict = json.loads(st.secrets["FIREBASE"])
    except:
        key_dict = st.secrets["FIREBASE"]
        
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

calls_ref = db.collection('nurse_calls').order_by("timestamp", direction=firestore.Query.DESCENDING).limit(20)
calls = [doc.to_dict() for doc in calls_ref.stream()]

if calls:
    df = pd.DataFrame(calls)
    
    # จัดการเวลา
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp']) + timedelta(hours=7)
        df['timestamp'] = df['timestamp'].dt.strftime('%d/%m/%Y %H:%M:%S')
 
    # ตรวจสอบว่ามีเคสที่ยังไม่ตอบหรือไม่ (ถ้ามี -> เล่นเสียง)
    has_unreplied = any(val is None or str(val).lower() in ['none', 'nan', ''] for val in df['reply_message'])
    if has_unreplied:
        play_alert_sound()

    def highlight_replied(row):
        val = row.get('reply_message')
        val_str = str(val).strip()
        if val_str == "" or val_str.lower() == "none" or val_str.lower() == "nan":
            return ['background-color: #fce4ec'] * len(row)
        else:
            return ['background-color: #e1bee7'] * len(row)

    st.subheader("สถานะเตียงในวอร์ด (ล่าสุด)")
    st.dataframe(df.style.apply(highlight_replied, axis=1), use_container_width=True)
else:
    st.info("ยังไม่มีคำขอเข้ามาในระบบ")

st.divider()
st.subheader("💬 ระบบตอบกลับคนไข้")
target_bed = st.number_input("ระบุเลขเตียง (ใส่เลข):", min_value=1, max_value=10, step=1)
reply_text = st.text_input("พิมพ์ข้อความตอบกลับ:")

if st.button("ส่งข้อความ"):
    target_bed_str = f"เตียง{target_bed}"
    pending_ref = db.collection('nurse_calls')\
                    .where("bed_id", "==", target_bed_str)\
                    .order_by("timestamp", direction=firestore.Query.DESCENDING)\
                    .limit(1)
    
    docs = list(pending_ref.stream())
    if docs:
        doc = docs[0]
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

