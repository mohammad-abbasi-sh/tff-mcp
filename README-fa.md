# tff-mcp 🇹🇷

mcp-name: io.github.mohammad-abbasi-sh/tff-mcp

سرور MCP غیررسمی و **فقط‌خواندنی** برای tff.org (فدراسیون فوتبال ترکیه — TFF) — جدول رده‌بندی (پوان جتورلی)، برنامه و نتایج بازی‌ها (فیکستور)، جزئیات کامل هر مسابقه و جدول گلزنان برتر (گل کرال‌لیغی) برای ۱۸ لیگ ترکیه، از سوپرلیگ تا لیگ‌های جوانان.

> ساختهٔ محمد عباسی در چارچوب «کارخانهٔ MCP ترکیه» (خط لوله به سبک سپهر). وابسته به tff.org یا TFF نیست.

## برای ایجنت‌های هوش مصنوعی

به پیکربندی کلاینت MCP خود اضافه کنید (stdio):

```json
{
  "mcpServers": {
    "tff": {
      "command": "uvx",
      "args": ["tff-mcp==0.1.1"]
    }
  }
}
```

یا به‌صورت محلی اجرا کنید: `python -m tff_mcp.server` (نیازمند `mcp<2` و `curl-cffi`).

## ابزارها

| ابزار | توضیح |
|------|--------|
| `tff_list_leagues` | ۱۸ لیگ تحت پوشش (slug، نام ترکی، شناسهٔ صفحهٔ TFF، چندگروهی بودن، وجود صفحهٔ گلزنان) |
| `tff_standings` | جدول رده‌بندی — `league` ‏(پیش‌فرض ‏«trendyol-super-lig»)؛ ‏`group` برای لیگ‌های چندگروهی: شمارهٔ گروه (‏«0»)، شناسهٔ گروه یا نام آن (‏«Kırmızı»، ‏«Beyaz»، ‏«01»)؛ رتبه، تیم، بازی/برد/مساوی/باخت، گل زده/خورده، تفاضل گل، امتیاز |
| `tff_fixtures` | برنامه و نتایج — `league`؛ ‏`week` برای فیلتر یک هفته؛ ‏`group` برای لیگ‌های چندگروهی؛ میزبان/میهمان، نتیجه (اگر بازی نشده باشد null)، وضعیت (‏«played»/«scheduled»)، شناسهٔ مسابقه در TFF و نشانی جزئیات مسابقه |
| `tff_match_detail` | جزئیات کامل یک مسابقه — `mac_id` (همان که `tff_fixtures` برمی‌گرداند، مثلاً ‏«317874»)؛ تیم‌ها و نتیجه، تاریخ و ساعت، ورزشگاه، لیگ/فصل، کد مسابقه، تیم داوری (داور، کمک‌داورها، VAR/AVAR، ناظر، نماینده)، گل‌ها با دقیقه، ترکیب اصلی هر دو تیم |
| `tff_top_scorers` | گلزنان برتر — `league`: ‏«trendyol-super-lig» (پیش‌فرض)، ‏«trendyol-1-lig»، ‏«nesine-2-lig» یا ‏«nesine-3-lig» (چهار لیگی که صفحهٔ گلزنان دارند)؛ ‏`limit` ‏۱ تا ۵۰ |

نمونهٔ خروجی (`tff_match_detail` / غازی‌انتپ ۰–۲ قاسم‌پاشا، ۶ نوامبر ۲۰۲۶):

```json
{"home": "GAZİANTEP FUTBOL KULÜBÜ A.Ş.", "away": "KASIMPAŞA A.Ş.",
 "score_home": 0, "score_away": 2, "date": "6.11.2026", "time": "20:00",
 "stadium": "GAZİANTEP STADYUMU - GAZİANTEP - ŞEHİTKAMİL",
 "league": "Trendyol Süper Lig Adnan Süvari Sezonu (Profesyonel Takım)",
 "match_code": "1091",
 "officials": [{"name": "ÜMİT ÖZTÜRK", "role": "Hakem"},
               {"name": "ERKAN ENGİN", "role": "VAR"}],
 "goals": [{"player": "HARIS HAJRADINOVIC", "minute": 3, "type": "F"},
           {"player": "ADRIAN DAWID BENEDYCZAK", "minute": 21, "type": "P"}]}
```

## چگونه کار می‌کند

tff.org صفحات لیگ را کاملاً سمت سرور رندر می‌کند — بدون ورود، کلید API و کوکی. جدول رده‌بندی در `<table class="s-table">` است (سربرگ O G B M A Y AV P)؛ فیکستور در `<table class="fiksturListesiTable">` (سطرهای سربرگ «N.Hafta» و سطرهای مسابقه با پیوند باشگاه میزبان، پیوند نتیجه `pageID=29&macId=...` و پیوند باشگاه میهمان — بازی‌های انجام‌نشده « - » نشان می‌دهند). لیگ‌های چندگروهی (نسینه ۲. لیگ، نسینه ۳. لیگ، BAL، لیگ‌های بانوان و جوانان) گروه‌هایشان را با پیوندهای `?pageID=<id>&grupID=<n>` نشان می‌دهند. در جزئیات مسابقه، تیم‌ها در `lnkTakim1`/`lnkTakim2`، نتیجه‌ها در spanهای `MacDetaySayi`، لیگ/فصل در `lblOrganizasyonAdi`، کد مسابقه در `lblKod`، تاریخ/ساعت در `lblTarih`، ورزشگاه در متن میان کد و تاریخ، داوران به‌صورت جفت‌های `NAME(ROLE)`، گل‌ها به شکل «NAME,3.dk (F)» و ترکیب‌های اصلی در تکرارکننده‌های `grdTakim1/2_rptKadrolar` هستند. گلزنان برتر از تکرارکنندهٔ `rptGolKralligi` می‌آیند (صفحات ۸۲۱/۸۲۲/۸۲۳/۸۲۴). سایت یک ASP.NET قدیمی با کدگذاری windows-1254 است و صریحاً دیکد می‌شود. یک قابلیت سایت جعل نمی‌شود، بلکه مستند شده است: صفحهٔ داوران هفته (`pageID=600`) هفته‌های لیگ ۲ و ۳ را با ستون‌های داوری خالی نشان می‌دهد — انتصاب‌ها نزدیک روز مسابقه اعلام می‌شوند — پس دادهٔ داوری از صفحهٔ جزئیات مسابقه گرفته می‌شود. انتقال با جعل TLS کروم است (`curl-cffi`، ‏`chrome120`)؛ درخواست‌ها با فاصلهٔ ~۰٫۸ ثانیه؛ همه‌چیز فقط‌خواندنی است.

## نصب

```bash
uvx tff-mcp==0.1.1        # اجرای مستقیم (نیازمند uv)
# یا
pip install tff-mcp==0.1.1
tff-mcp    # سرور MCP را روی stdio راه می‌اندازد
```

## تست‌ها

```bash
python -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python -m unittest discover -s tests -v
```

تست‌های آفلاین روی فیکسچرهای ضبط‌شده اجرا می‌شوند (صفحات واقعی در ۲۰۲۶-۱۱-۰۹ گرفته شده‌اند)؛ تست‌های زنده به tff.org می‌روند. در زمان ساخت ۳۷/۳۷ سبز (۲۰ آفلاین + ۱۷ زنده) به‌علاوهٔ یک تست دودی MCP روی stdio.

## نقشهٔ راه

- آرای انضباطی (صفحات PFDK/AFDK) و بازیکنان محروم (pageID=633)
- صفحات باشگاه‌ها (pageID=28&kulupID=...) — فهرست بازیکنان
- بازی‌های تیم ملی (pageID=425)

## مجوز

MIT — ببینید [LICENSE](LICENSE).

---

Built by [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
