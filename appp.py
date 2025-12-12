import streamlit as st
import requests

# -----------------------
# Sayfa
# -----------------------
st.set_page_config(page_title="TalepBazlı Emlak", layout="centered")

# -----------------------
# API URL
# Secrets'ta API_URL varsa onu kullanır.
# Yoksa alttaki default'u kullanır (gerekirse port ekle: :8000 gibi)
# -----------------------
API_URL = st.secrets.get("API_URL", "http://46.1.155.61:8000").rstrip("/")

# -----------------------
# Yardımcı fonksiyonlar
# -----------------------
def api_get(path: str):
    return requests.get(f"{API_URL}{path}", timeout=8)

def api_post(path: str, payload: dict):
    return requests.post(f"{API_URL}{path}", json=payload, timeout=12)

def backend_check():
    """Backend yaşıyor mu? / dene."""
    try:
        r = api_get("/")
        return (r.status_code == 200), f"GET / -> {r.status_code} {r.text[:120]}"
    except Exception as e:
        return False, repr(e)

@st.cache_data(ttl=10)
def fetch_requests():
    r = api_get("/requests")
    r.raise_for_status()
    return r.json()

# -----------------------
# UI
# -----------------------
st.title("TalepBazlı Emlak (Ters Sahibinden)")
st.caption(f"API_URL: {API_URL}")

ok, info = backend_check()
if ok:
    st.success(f"Backend OK ✅  ({info})")
else:
    st.error("Backend'e bağlanılamıyor ❌")
    st.code(info)

tab1, tab2 = st.tabs(["Talep Oluştur", "Talepleri Gör"])

# -----------------------
# TAB 1: Talep oluştur
# -----------------------
with tab1:
    st.subheader("Yeni Talep Oluştur")

    user_id = st.number_input("User ID", min_value=1, step=1)
    title = st.text_input("Başlık", "Mudanya Trilye 3+1 max 7M")
    city = st.text_input("Şehir", "Bursa")
    district = st.text_input("İlçe", "Mudanya")
    neighbourhood = st.text_input("Mahalle", "Trilye")
    budget_max = st.number_input("Max Bütçe", min_value=0, step=100000, value=7000000)
    rooms = st.text_input("Oda seçenekleri (virgülle)", "3+1")

    if st.button("Talep Oluştur", type="primary", disabled=not ok):
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
            r = api_post("/requests", payload)
            st.write("POST /requests status:", r.status_code)

            if r.status_code in (200, 201):
                st.success("Talep oluşturuldu ✅")
                st.json(r.json())

                # Listeyi güncelle
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Talep oluşturulamadı")
                st.text(r.text[:2000])

        except Exception as e:
            st.error("Backend'e bağlanılamadı (POST).")
            st.code(repr(e))

# -----------------------
# TAB 2: Talepleri gör
# -----------------------
with tab2:
    st.subheader("Aktif Talepler")

    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("Listeyi Yenile"):
            st.cache_data.clear()
            st.rerun()

    if not ok:
        st.warning("Backend bağlantısı yoksa talepler çekilemez. API_URL/port veya deploy kontrol et.")
    else:
        try:
            data = fetch_requests()
            if not data:
                st.info("Henüz hiç talep yok. 'Talep Oluştur' sekmesinden ekle.")
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

        except Exception as e:
            st.error("Backend'e bağlanılamadı (GET).")
            st.code(repr(e))
