import streamlit as st
import requests

API_URL = st.secrets.get("API_URL", "http://46.1.155.61")


st.title("TalepBazlı Emlak (Ters Sahibinden)")

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

    if st.button("Talep Oluştur"):
        payload = {
            "user_id": int(user_id),
            "title": title,
            "description": "",
            "city": city,
            "district": district,
            "neighbourhood": neighbourhood,
            "budget_min": 0,
            "budget_max": float(budget_max),
            "room_options": [r.strip() for r in rooms.split(",")]
        }
        r = requests.post(f"{API_URL}/requests", json=payload)
        if r.status_code in (200, 201):
            st.success("Talep oluşturuldu ✅")
            st.json(r.json())
        else:
            st.error(f"Hata: {r.status_code}")
            st.text(r.text)

with tab2:
    st.subheader("Aktif Talepler")
    r = requests.get(f"{API_URL}/requests")
    if r.status_code == 200:
        for item in r.json():
            st.write(f"**{item['title']}** — {item['city']}/{item['district']} — max {item['budget_max']} TL")
            st.caption(f"Oda: {', '.join(item['room_options'])}")
            st.divider()
    else:
        st.error("API erişilemiyor. Backend çalışıyor mu?")
