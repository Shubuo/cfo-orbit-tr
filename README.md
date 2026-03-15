# Personal CFO & Portfolio Manager (Turkey)

Turkiye finansal piyasalarina (BIST 100, TEFAS fonlari, TUİK enflasyon) odaklanan, CrewAI tabanli cok‑ajanli bir "Personal CFO" sistemi. Gercek zamanli veri cekimi, risk toleransina gore portfoy stratejisi ve Turkce raporlama sunar.

## Ozellikler
- **Sequential CrewAI**: Veri toplama -> strateji -> raporlama.
- **BIST 100 / TEFAS / TUİK** veri kaynaklari (borsapy + tefasfon).
- **Terminal gorsellestirme**: plotext ile portfoy dagilimi.
- **Gizlilik odakli**: API anahtari sadece runtime'da istenir.

## Kurulum
1. Python 3.10+ kurulu olmali.
2. Bagimliliklari yukleyin:
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
3. `.env` dosyasi hazirlayin (opsiyonel):
```
cp .env.example .env
```
4. `.env` icine `GEMINI_API_KEY` yazin veya runtime'da girin.

## Calistirma
```
python main.py
```
Calistirma sirasinda:
- `GEMINI_API_KEY` (yoksa sorulur)
- Risk toleransi (Low/Medium/High)
- Yatirim sermayesi (TL)

Rapor: `monthly_cfo_report.md` olarak uretilir.

## Non-Interactive Mod
CI/cron icin:
```
export GEMINI_API_KEY=...
export RISK_TOLERANCE=Low
export INVESTMENT_CAPITAL=250000
python main.py --non-interactive
```

## Model Ayari
Varsayilanlar `gemini-2.5-flash` ve `gemini-2.5-pro` olarak gelir.
Diger isimler icin:
```
export GEMINI_FLASH_MODEL=gemini-2.0-flash
export GEMINI_PRO_MODEL=gemini-pro-latest
```
Istersen yedek modelleri de belirtebilirsin:
```
export GEMINI_FLASH_FALLBACK=gemini-2.0-flash,gemini-flash-latest
export GEMINI_PRO_FALLBACK=gemini-pro-latest,gemini-2.0-flash
```
Pro kotasi yoksa otomatik flash kullanmak icin:
```
export GEMINI_FORCE_FLASH_FOR_PRO=true
```
Mevcut modelleri listelemek icin:
```
python main.py --list-models
```

## Smoke Test
Bagimlilik kurmadan sadece temel yapisal kontrol icin:
```
python scripts/smoke.py
```

## Ornek Cikti
```
Baslik: Aylik Kisisel CFO Ozeti

Kisa Vade (0-6 ay)
- Hedef Dagilim: Hisse 35%, Sabit Getiri 45%, Emtia 20%
- Eylem Plani: Likidite ve enflasyon korumasi odakli.

Orta Vade (6-24 ay)
- Hedef Dagilim: Hisse 45%, Sabit Getiri 35%, Emtia 20%
- Eylem Plani: Secici BIST 100 ve nitelikli fonlar.

Uzun Vade (2+ yil)
- Hedef Dagilim: Hisse 60%, Sabit Getiri 25%, Emtia 15%
- Eylem Plani: Buyume odakli ve risk dengeli portfoy.
```

## Mimarî
**Agent 1 – Data Collector & Analyst**
- TUİK enflasyon (CPI/PPI)
- TEFAS en iyi fonlar
- BIST 100 yuksek likidite

**Agent 2 – Financial Strategist**
- Risk toleransina gore portfoy
- 3 vade: 0‑6 ay, 6‑24 ay, 2+ yil

**Agent 3 – Reporting Specialist & CFO**
- Turkce rapor + terminal ozeti
- plotext ile portfoy dagilimi

## Klasor Yapisi
```
.
├─ agents.py
├─ tasks.py
├─ tools.py
├─ main.py
├─ requirements.txt
├─ .env.example
└─ README.md
```

## Katki (PR)
Katki yapmak icin:
1. Fork -> branch acin (`feat/...` ya da `fix/...`)
2. Kod ve testleri guncelleyin
3. PR acin

Detaylar icin `CONTRIBUTING.md`.

## Uyari
Bu proje **yatirim tavsiyesi degildir**. Bilgilendirme amaclidir.
