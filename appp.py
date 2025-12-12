import streamlit as st
import requests

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="TalepBazlı Emlak", layout="centered")

# Secrets varsa onu kullan, yoksa default
API_URL = st.secrets.get("API_URL", "http://46.1.155.61:8000").rstrip("/")

# =========================
# HELPERS
# =========================
def api_get(path: str):
    return requests.get(f"{API_URL}{path}", timeout=8)

def api_post(path: str, payload: dict):
    return requests.post(f"{API_URL}{path}", json=payload, timeout=12)

@st.cache_data(ttl=10)
def fetch_requests_cached():
    r = api_get("/requests")
    r.raise_for_status()
    return r.json()

def check_backend():
    """
    Backend canlı mı?
    /health yoksa / ile dener.
    """
    try:
        r = api_get("/health")
        if r.status_code == 200:
            return True, f"/health OK: {r.text[:200]}"
    except Exception:
        pass

    try:
        r = api_get("/")
        if r.status_code == 200:
            return True, f"/ OK: {r.text[:200]}"
        return False, f"/ status={r.status_code} body={r.text[:200]}"
    except Exception as e:
        return False, repr(e)

# =========================
# UI
# =========================
st.title("TalepBazlı Emlak (Ters Sahibinden)")
st.caption(f"API_URL: {API_URL}")

ok, msg = check_backend()
if ok:
    st.success(f"Backend bağlantısı OK ✅  ({msg})")
else:
    st.error("Backend'e bağlanılamıyor ❌")
    st.code(msg)

tab1, tab2 = st.tabs(["Talep Oluştur", "Talepleri Gör"])

# =========================
# TAB 1: CREATE REQUEST
# =========================
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
            if r.status_code in (200, 201):
                st.success("Talep oluşturuldu ✅")
                st.json(r.json())

                # 🔥 Listeyi anında güncelle
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(f"Hata: {r.status_code}")
                st.text(r.text[:2000])

        except requests.exceptions.RequestException as e:
            st.error("Talep oluşturulamadı (backend erişim sorunu).")
            st.code(repr(e))

# =========================
# TAB 2: LIST REQUESTS
# =========================
with tab2:
    st.subheader("Aktif Talepler")

    c1, c2 = st.columns([1, 2])
    with c1:
        if st.button("Listeyi Yenile"):
            st.cache_data.clear()
            st.rerun()

    if not ok:
        st.warning("Backend kapalıysa liste çekilemez. Önce API_URL/port doğru mu kontrol et.")
    else:
        try:
            data = fetch_requests_cached()

            if not data:
                st.info("Henüz hiç talep yok. 'Talep Oluştur' sekmesinden ekle.")
            else:
                for item in data:
                    st.write(
                        f"**{item.get('title','-')}** — "
                        f"{item.get('city','-')}/{item.get('district','-')} — "
                        f"max {item.get('budget_max','-')} TL"
                    )
                    rooms_list = item.get("room_options") or []
                    if isinstance(rooms_list, list):
                        st.caption(f"Oda: {', '.join(rooms_list)}")
                    else:
                        st.caption(f"Oda: {rooms_list}")
                    st.divider()

        except requests.exceptions.RequestException as e:
            st.error("Talepler çekilemedi. API erişilemiyor veya backend kapalı.")
            st.code(repr(e))
        except Exception as e:
            st.error("Beklenmeyen hata.")
            st.code(repr(e))
