import hashlib
import io
import sqlite3
import pandas as pd
import streamlit as st

# ==========================================
# 1. VERİTABANI VE TABLO KURULUMU
# ==========================================
conn = sqlite3.connect("belge_portal.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
""")
c.execute("""
    CREATE TABLE IF NOT EXISTS duyurular (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        baslik TEXT,
        icerik TEXT,
        tarih TEXT
    )
""")
c.execute("""
    CREATE TABLE IF NOT EXISTS sinavlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meslek TEXT,
        tarih TEXT,
        yer TEXT
    )
""")
c.execute("""
    CREATE TABLE IF NOT EXISTS adaylar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ad_soyad TEXT,
        tc_no TEXT,
        meslek TEXT,
        telefon TEXT
    )
""")
c.execute("""
    CREATE TABLE IF NOT EXISTS sinav_sonuclari (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tc_no TEXT,
        meslek TEXT,
        puan INTEGER,
        durum TEXT
    )
""")
conn.commit()


# Varsayılan Admin Hesabı Oluştur (Kullanıcı: admin, Şifre: 12345)
def create_default_admin():
  c.execute("SELECT * FROM users WHERE username = 'admin'")
  if not c.fetchone():
    hashed_pw = hashlib.sha256("12345".encode()).hexdigest()
    c.execute(
        "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
        ("admin", hashed_pw, "Sistem Yöneticisi"),
    )
    conn.commit()


create_default_admin()

# ==========================================
# 2. SAYFA YAPILANDIRMASI VE MENÜ
# ==========================================
st.set_page_config(
    page_title="Belgelendirme Portalı", page_icon="🎓", layout="wide"
)

# Oturum Durumu Kontrolü
if "logged_in" not in st.session_state:
  st.session_state.logged_in = False
  st.session_state.username = ""
  st.session_state.role = ""

st.sidebar.title("🎓 Belgelendirme Portalı")
st.sidebar.caption("ONLINE İŞLEM MERKEZİ")

# Benzersiz key eklendi
menu = st.sidebar.radio(
    "Menü",
    [
        "Anasayfa",
        "Sınav Takvimi",
        "Duyurular",
        "Belge Sorgulama",
        "İletişim",
        "Yönetici Portalı (Giriş)",
    ],
    key="ana_navigasyon_menu",
)

# ==========================================
# 3. SAYFA İÇERİKLERİ
# ==========================================
if menu == "Anasayfa":
  st.title("Hoş Geldiniz - Belgelendirme Portalı")
  st.write(
      "Bu platform üzerinden mesleki yeterlilik sınav takvimlerini"
      " inceleyebilir, güncel duyuruları takip edebilir ve belge"
      " sorgulaması yapabilirsiniz."
  )
  st.info(
      "💡 Yönetim işlemlerine erişmek için sol menüden **Yönetici Portalı"
      " (Giriş)** sekmesini seçebilirsiniz."
  )

elif menu == "Sınav Takvimi":
  st.title("📅 Sınav Takvimi")
  df_sinav = pd.read_sql_query("SELECT * FROM sinavlar ORDER BY id DESC", conn)
  if not df_sinav.empty:
    st.dataframe(
        df_sinav.drop(columns=["id"]), use_container_width=True, hide_index=True
    )
  else:
    st.info("Planlanmış aktif sınav takvimi bulunmamaktadır.")

elif menu == "Duyurular":
  st.title("📢 Duyurular")
  df_duyuru = pd.read_sql_query(
      "SELECT * FROM duyurular ORDER BY id DESC", conn
  )
  if not df_duyuru.empty:
    for _, row in df_duyuru.iterrows():
      st.subheader(row["baslik"])
      st.caption(f"Yayın Tarihi: {row['tarih']}")
      st.write(row["icerik"])
      st.divider()
  else:
    st.info("Henüz yayınlanmış bir duyuru bulunmuyor.")

elif menu == "Belge Sorgulama":
  st.title("🔍 Belge ve Sınav Sonucu Sorgulama")
  # Benzersiz key eklendi
  tc_sorgu = st.text_input(
      "T.C. Kimlik Numaranızı Girin", key="aday_tc_sorgu_input"
  )
  if st.button("Sorgula", key="aday_sorgula_btn"):
    if tc_sorgu:
      df_sonuc_sorgu = pd.read_sql_query(
          "SELECT meslek, puan, durum FROM sinav_sonuclari WHERE tc_no = ?",
          conn,
          params=(tc_sorgu,),
      )
      if not df_sonuc_sorgu.empty:
        st.success("Sınav sonucunuz bulundu:")
        st.dataframe(df_sonuc_sorgu, use_container_width=True, hide_index=True)
      else:
        st.warning("Bu T.C. Numarasına ait aktif bir sınav sonucu bulunamadı.")
    else:
      st.warning("Lütfen geçerli bir T.C. Kimlik Numarası giriniz.")

elif menu == "İletişim":
  st.title("📞 İletişim Bilgileri")
  st.write("Sorularınız, görüş ve önerileriniz için bizimle iletişime geçin.")
  with st.form("iletisim_form"):
    st.text_input("Ad Soyad", key="iletisim_ad_input")
    st.text_input("E-posta Adresi", key="iletisim_eposta_input")
    st.text_area("Mesajınız", key="iletisim_mesaj_input")
    if st.form_submit_button("Gönder"):
      st.success("Mesajınız başarıyla iletildi.")

# ==========================================
# 4. YÖNETİCİ PORTALI VE PANEL
# ==========================================
elif menu == "Yönetici Portalı (Giriş)":
  st.title("🔐 Yönetici Portalı")

  if not st.session_state.logged_in:
    st.write("Giriş için kullanıcı bilgilerinizi doldurun.")
    with st.form("login_form"):
      # Benzersiz keyler eklendi
      username = st.text_input("Kullanıcı Adı", key="admin_login_username")
      password = st.text_input(
          "Şifre", type="password", key="admin_login_password"
      )
      submit = st.form_submit_button("Giriş Yap")

      if submit:
        hashed_input = hashlib.sha256(password.encode()).hexdigest()
        c.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, hashed_input),
        )
        user = c.fetchone()
        if user:
          st.session_state.logged_in = True
          st.session_state.username = user[1]
          st.session_state.role = user[3]
          st.success("Giriş başarılı! Yönlendiriliyorsunuz...")
          st.rerun()
        else:
          st.error("Kullanıcı adı veya şifre hatalı!")
    st.caption("Varsayılan Admin Bilgileri -> Kullanıcı Adı: `admin` | Şifre: `12345`")
  else:
    st.success(
        f"Giriş Yapıldı: **{st.session_state.username}**"
        f" ({st.session_state.role})"
    )
    if st.button("Çıkış Yap", key="admin_cikis_btn"):
      st.session_state.logged_in = False
      st.session_state.username = ""
      st.session_state.role = ""
      st.rerun()

    st.markdown("---")
    st.subheader("⚙️ Yönetim Paneli")
    # Benzersiz key eklendi
    admin_tab = st.selectbox(
        "Yönetim İşlemi Seçin",
        [
            "Duyuru Ekle",
            "Sınav Ekle",
            "Aday Kaydı Ekle",
            "Sınav Sonucu Gir",
            "Excel ile Toplu Aday Yükle",
            "Kayıtlı Listeler",
        ],
        key="yonetim_panel_sekme_secimi",
    )

    if admin_tab == "Duyuru Ekle":
      with st.form("add_duyuru"):
        b_baslik = st.text_input("Duyuru Başlığı", key="duyuru_baslik_input")
        b_icerik = st.text_area("Duyuru İçeriği", key="duyuru_icerik_input")
        b_tarih = st.date_input("Duyuru Tarihi", key="duyuru_tarih_input")
        if st.form_submit_button("Yayınla"):
          c.execute(
              "INSERT INTO duyurular (baslik, icerik, tarih) VALUES (?, ?, ?)",
              (b_baslik, b_icerik, str(b_tarih)),
          )
          conn.commit()
          st.success("Duyuru eklendi!")

    elif admin_tab == "Sınav Ekle":
      with st.form("add_sinav"):
        s_meslek = st.text_input(
            "Meslek / Sınav Adı", key="sinav_meslek_input"
        )
        s_tarih = st.date_input("Sınav Tarihi", key="sinav_tarih_input")
        s_yer = st.text_input("Sınav Yeri / Şehir", key="sinav_yer_input")
        if st.form_submit_button("Kaydet"):
          c.execute(
              "INSERT INTO sinavlar (meslek, tarih, yer) VALUES (?, ?, ?)",
              (s_meslek, str(s_tarih), s_yer),
          )
          conn.commit()
          st.success("Sınav takvime eklendi!")

    elif admin_tab == "Aday Kaydı Ekle":
      with st.form("add_aday"):
        st.write("Yeni Sınav Adayı Kaydı")
        a_ad = st.text_input("Adı Soyadı", key="aday_ad_input")
        a_tc = st.text_input("T.C. Kimlik Numarası", key="aday_tc_input")
        a_meslek = st.text_input(
            "Başvurduğu Meslek / Sertifika", key="aday_meslek_input"
        )
        a_tel = st.text_input("Telefon Numarası", key="aday_tel_input")
        if st.form_submit_button("Adayı Kaydet"):
          if a_ad and a_tc:
            c.execute(
                "INSERT INTO adaylar (ad_soyad, tc_no, meslek, telefon) VALUES"
                " (?, ?, ?, ?)",
                (a_ad, a_tc, a_meslek, a_tel),
            )
            conn.commit()
            st.success(f"'{a_ad}' isimli aday başarıyla kaydedildi!")
          else:
            st.warning("Lütfen Ad Soyad ve T.C. Kimlik alanlarını doldurun.")

    elif admin_tab == "Sınav Sonucu Gir":
      with st.form("add_sonuc"):
        st.write("Sınav Sonucu Giriş Paneli")
        s_tc = st.text_input(
            "Aday T.C. Kimlik Numarası", key="sonuc_tc_input"
        )
        s_meslek = st.text_input("Meslek Adı", key="sonuc_meslek_input")
        s_puan = st.number_input(
            "Sınav Puanı", min_value=0, max_value=100, key="sonuc_puan_input"
        )
        s_durum = st.selectbox(
            "Sınav Durumu",
            ["Başarılı", "Başarısız"],
            key="sonuc_durum_select",
        )
        if st.form_submit_button("Sonucu Kaydet"):
          if s_tc:
            c.execute(
                "INSERT INTO sinav_sonuclari (tc_no, meslek, puan, durum)"
                " VALUES (?, ?, ?, ?)",
                (s_tc, s_meslek, s_puan, s_durum),
            )
            conn.commit()
            st.success("Sınav sonucu sisteme işlendi!")
          else:
            st.warning("Lütfen T.C. Kimlik numarasını giriniz.")

    elif admin_tab == "Excel ile Toplu Aday Yükle":
      st.subheader("📁 Excel ile Toplu Aday Kaydı Yükleme")
      st.write(
          "Excel dosyanızda şu sütun adları olmalıdır: **ad_soyad**, **tc_no**,"
          " **meslek**, **telefon**"
      )
      # Benzersiz key eklendi
      uploaded_file = st.file_uploader(
          "Aday Listesi Excel Dosyasını Seçin",
          type=["xlsx", "xls"],
          key="excel_toplu_aday_uploader",
      )

      if uploaded_file is not None:
        try:
          df_import = pd.read_excel(uploaded_file)
          gerekli_sutunlar = ["ad_soyad", "tc_no", "meslek", "telefon"]
          eksik_sutunlar = [
              s for s in gerekli_sutunlar if s not in df_import.columns
          ]

          if not eksik_sutunlar:
            st.write("Önizleme (İlk 5 Satır):")
            st.dataframe(df_import.head(), use_container_width=True)

            # Benzersiz key eklendi
            if st.button(
                "Verileri Veritabanına Aktar", key="verileri_aktar_btn"
            ):
              basarili_sayisi = 0
              for _, row in df_import.iterrows():
                try:
                  c.execute(
                      "INSERT INTO adaylar (ad_soyad, tc_no, meslek, telefon)"
                      " VALUES (?, ?, ?, ?)",
                      (
                          str(row["ad_soyad"]),
                          str(row["tc_no"]),
                          str(row["meslek"]),
                          str(row["telefon"]),
                      ),
                  )
                  basarili_sayisi += 1
                except Exception:
                  pass
              conn.commit()
              st.success(
                  f"🎉 Toplam {basarili_sayisi} aday başarıyla sisteme eklendi!"
              )
          else:
            st.error(
                f"Excel dosyanızda şu zorunlu sütunlar eksik:"
                f" {', '.join(eksik_sutunlar)}"
            )
        except Exception as e:
          st.error(f"Dosya okunurken bir hata oluştu: {e}")

    elif admin_tab == "Kayıtlı Listeler":
      st.subheader("📋 Sistemdeki Veriler ve Dışa Aktarım")
      # Benzersiz key eklendi
      secim_liste = st.selectbox(
          "Görüntülenecek Tablo",
          ["Adaylar Listesi", "Sınav Sonuçları Listesi"],
          key="kayitli_liste_goruntule_select",
      )

      if secim_liste == "Adaylar Listesi":
        df_aday = pd.read_sql_query("SELECT * FROM adaylar", conn)
        st.dataframe(df_aday, use_container_width=True)

        if not df_aday.empty:
          output = io.BytesIO()
          with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_aday.to_excel(writer, index=False, sheet_name="Adaylar")
          excel_data = output.getvalue()

          # Benzersiz key eklendi
          st.download_button(
              label="📥 Aday Listesini Excel Olarak İndir",
              data=excel_data,
              file_name="aday_listesi.xlsx",
              mime=(
                  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              ),
              key="aday_excel_indir_btn",
          )
        else:
          st.info("İndirilecek aday kaydı bulunmuyor.")

      else:
        df_sonuc = pd.read_sql_query("SELECT * FROM sinav_sonuclari", conn)
        st.dataframe(df_sonuc, use_container_width=True)

        if not df_sonuc.empty:
          output = io.BytesIO()
          with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_sonuc.to_excel(
                writer, index=False, sheet_name="Sinav Sonuclari"
            )
          excel_data = output.getvalue()

          # Benzersiz key eklendi
          st.download_button(
              label="📥 Sınav Sonuçlarını Excel Olarak İndir",
              data=excel_data,
              file_name="sinav_sonuclari.xlsx",
              mime=(
                  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              ),
              key="sonuc_excel_indir_btn",
          )
        else:
          st.info("İndirilecek sınav sonucu kaydı bulunmuyor.")
