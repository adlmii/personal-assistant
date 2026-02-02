# 🟦 SPRINT — Calm, Fast-Feeling Conversational Kevin

## 🎯 Sprint Goal
Membuat Kevin terasa seperti **teman ngobrol dan partner mikir yang tenang**, dengan respons yang **cepat secara rasa**, **tanpa dead air**, **tanpa nyela**, serta tetap mampu melakukan **kontrol PC sederhana** dan **mengingat preferensi user** secara natural.

Sprint ini fokus pada **UX percakapan**, bukan penambahan fitur besar.

---

## 🧍 Persona (Locked)
- Pendengar yang sopan
- Partner mikir (clarify > assume)
- Operator ringan (musik, buka app, basic control)

---

## 🚫 Non-Goal
Sprint ini **TIDAK** mencakup:
- Multi-step planner / steps[]
- Automation kerja kompleks
- Autonomous / proactive interrupt
- Background daemon
- Skill chaining lanjutan

---

## 🧩 Sprint Epics

### 🧠 EPIC 1 — Calm Presence (Anti Dead Air)
**Problem:** Kevin sering terasa “hilang” saat mikir  
**Target:** User selalu tahu Kevin sedang memproses

**Outcome:**
- Kevin selalu memberi 1 soft acknowledgement
- Tidak ada silent gap > ~700ms
- Tidak cerewet / filler berlebihan

---

### ⚡ EPIC 2 — Fast-Feeling Response Flow
**Problem:** Respon terasa lama karena menunggu keputusan sempurna  
**Target:** Respon terasa cepat walaupun reasoning berat berjalan di belakang

**Outcome:**
- Ack muncul sebelum reasoning berat selesai
- Command sederhana dieksekusi cepat
- Jawaban singkat dan utuh

---

### 🧠 EPIC 3 — Accurate Intent (Less Salah Nangkap)
**Problem:** Kevin kadang salah asumsi intent  
**Target:** Kevin lebih sering klarifikasi daripada salah eksekusi

**Outcome:**
- Ambigu → clarifying question
- Confidence rendah → no action
- Command vs conversation terklasifikasi jelas

---

### 🗂️ EPIC 4 — Familiar Memory (Kerasa Inget User)
**Problem:** Memory ada tapi belum terasa personal  
**Target:** Kevin mengingat user secara implisit, bukan eksplisit

**Outcome:**
- Preference dan fact diprioritaskan
- Memory digunakan di respon, tidak diumumkan
- Memory type `skip` benar-benar tidak tersimpan

---

## 📋 Sprint Backlog

### 🧠 EPIC 1 — Calm Presence
- [ ] Tambah soft acknowledgement (1 kata / 1 frase) sebelum think berat
- [ ] Pastikan hanya 1 acknowledgement per input
- [ ] Hilangkan filler berulang / speech loop

---

### ⚡ EPIC 2 — Fast-Feeling Flow
- [ ] Pisahkan flow: acknowledge → think → respond
- [ ] Eksekusi action ringan tanpa menunggu respon panjang
- [ ] Batasi jawaban command ke ≤ 1–2 kalimat

---

### 🧠 EPIC 3 — Intent Accuracy
- [ ] Tambah early intent check (command vs conversation)
- [ ] Confidence di bawah threshold → clarifying question
- [ ] Larang eksekusi action jika intent ambigu

---

### 🗂️ EPIC 4 — Familiar Memory
- [ ] Prioritaskan memory type `preference` dan `fact`
- [ ] Gunakan preference dalam respon (musik, app, dll)
- [ ] Pastikan memory type `skip` tidak pernah disimpan

---

## 🔄 Perubahan Flow Kevin

### Sebelum (1-LLM-1-Shot)
```scss
User
→ Think (lama)
→ Speak
→ Action
```

### Sebelum (SPRINT INI)
```scss
User
→ Soft Ack (cepat, tenang)
→ Think (async)
→ Short, clear response
→ (Optional) Action ringan
```
Kevin boleh diem sebentar,
tapi user selalu tau dia ada.

---

## 🧪 DEFINISI DONE (HUMAN METRICS)
Sprint ini dianggap selesai kalau:
- Lu gak lagi ngerasa “kok dia lama”
- Kevin jarang salah eksekusi
- Jawaban terasa nyambung & gak kebanyakan
- Lu nyaman ngobrol sambil mikir
Kalau lu ngerasa Kevin kayak partner diskusi, bukan alat — DONE ✅

---

## 🔜 NEXT (SETELAH SPRINT)
Setelah ini stabil:
- Sprint berikutnya baru Planner / Multi-step
- atau Autonomy ringan
- atau Background mode