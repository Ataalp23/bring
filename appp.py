import streamlit as st
import requests

st.set_page_config(page_title="TalepBazlı Emlak", layout="centered")

API_URL = st.secrets.get("API_URL", "http://46.1.155.61:8000").rstrip("/")

st.title("TalepBazlı Emlak (Ters Sahibinden)")
st.caption(f"API_URL: {API_URL}")

tab1, tab2 = st.tabs(["Talep Oluştur", "Talepleri Gör"])

with tab1:
    st.subheader("Yeni Talep Oluştur")

    user_id = st.number_input("User ID", min_value=1, step=1)
    title = st.text_input("Başlık", "Mudanya Trilye 3+1 max 7M")
    city = st.text_input("Şehir", "Bursa")
    district = st.text_input("İlçe", "Mudanya")
    neighbourhood = st.text_input("Mahalle", "Trilye")
    budget_max = st.number_input("Max Bütçe", min_value=0, step=100000, value=7000000)
    rooms = st.text_input("Oda seçenekleri (virgülle)", "3+1")

    if st.button("Talep Oluştur", type="primary"):
        payload = {
            "user_id": int(user_id),
            "title": title,
            "description": "",
            "city": city,
            "district": district,
            "neighbourhood": neighbourhood,
            "budget_min": 0,
            "budget_max": float(budget_max),
            "room_options": [r.strip() for r in rooms.split(",") if r.strip()],
        }

        try:
            r = requests.post(f"{API_URL}/requests", json=payload, timeout=10)
            st.write("POST status:", r.status_code)
            if r.status_code in (200, 201):
                st.success("Talep oluşturuldu ✅")
                st.json(r.json())
                st.rerun()
            else:
                st.error("Talep oluşturulamadı")
                st.text(r.text[:2000])
        except Exception as e:
            st.error("Backend'e bağlanılamadı (POST).")
            st.code(repr(e))

with tab2:
    st.subheader("Aktif Talepler")

    if st.button("Listeyi Yenile"):
        st.rerun()

    try:
        r = requests.get(f"{API_URL}/requests", timeout=10)
        st.write("GET status:", r.status_code)

        if r.status_code == 200:
            data = r.json()
            if not data:
                st.info("Henüz talep yok.")
            else:
                for item in data:
                    st.write(
                        f"**{item.get('title','-')}** — "
                        f"{item.get('city','-')}/{item.get('district','-')} — "
                        f"max {item.get('budget_max','-')} TL"
                    )
                    ro = item.get("room_options") or []
                    st.caption("Oda: " + (", ".join(ro) if isinstance(ro, list) else str(ro)))
                    st.divider()
        else:
            st.error("GET /requests hata verdi")
            st.text(r.text[:2000])

    except Exception as e:
        st.error("Backend'e bağlanılamadı (GET).")
        st.code(repr(e))
