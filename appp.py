import streamlit as st
import requests

# -----------------------
# API URL
# -----------------------
API_URL = st.secrets.get("API_URL", "http://46.1.155.61")  # gerekirse :8000 ekle

st.set_page_config(page_title="TalepBazlı Emlak", layout="centered")
st.title("TalepBazlı Emlak (Ters Sahibinden)")

# -----------------------
# Helpers
# -----------------------
@st.cache_data(ttl=10)
def fetch_requests(api_url: str):
    r = requests.get(f"{api_url}/requests", timeout=10)
    r.raise_for_status()
    return r.json()

def safe_post(url: str, payload: dict):
    r = requests.post(url, json=payload, timeout=15)
    # 4xx/5xx ise hata fırlatsın ki aşağıda yakalayalım
    r.raise_for_status()
    return r

# -----------------------
# Tabs
# -----------------------
tab1, tab2 = st.tabs(["Talep Oluştur", "Talepleri Gör"])

with tab1:
    st.subheader("Yeni Talep Oluştur")

    # Kullanıcı
    user_id = st.number_input("User ID", min_value=1, step=1)

    # Talep bilgileri
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
            resp = safe_post(f"{API_URL}/requests", payload)
            st.success("Talep oluşturuldu ✅")
            st.json(resp.json())

            # 🔥 Listeyi anında güncelle
            st.cache_data.clear()
            st.rerun()

        except requests.exceptions.RequestException as e:
            st.error("Talep oluşturulamadı. Backend/URL kontrol et.")
            st.caption("Detay:")
            st.code(str(e))

with tab2:
    st.subheader("Aktif Talepler")

    # Kullanıcı API URL'yi görsün (debug için iyi)
    st.caption(f"API_URL: {API_URL}")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Listeyi Yenile"):
            st.cache_data.clear()
            st.rerun()

    # Listeleme
    try:
        data = fetch_requests(API_URL)

        if not data:
            st.info("Henüz hiç talep yok. Önce 'Talep Oluştur' sekmesinden ekle.")
        else:
            for item in data:
                title = item.get("title", "-")
                city = item.get("city", "-")
                district = item.get("district", "-")
                budget_max = item.get("budget_max", "-")
                room_options = item.get("room_options") or []

                st.write(f"**{title}** — {city}/{district} — max {budget_max} TL")
                if isinstance(room_options, list):
                    st.caption(f"Oda: {', '.join(room_options)}")
                else:
                    st.caption(f"Oda: {room_options}")
                st.divider()

    except requests.exceptions.RequestException as e:
        st.error("Talepler çekilemedi. API erişilemiyor veya backend kapalı.")
        st.caption("Detay:")
        st.code(str(e))
