# tff-mcp 🇹🇷

mcp-name: io.github.mohammad-abbasi-sh/tff-mcp

tff.org (Türkiye Futbol Federasyonu — TFF) için resmi olmayan **salt okunur** MCP sunucusu — Süper Lig'den gençlik gelişim liglerine kadar 18 Türkiye liginde puan cetveli, fikstür ve sonuçlar, maç detayları ve gol krallığı.

> Mohammad Abbasi tarafından "Turkey MCP factory" (Sepehr tarzı hat) kapsamında geliştirildi. tff.org veya TFF ile bağlantısı yoktur.

## Yapay zekâ ajanları için

MCP istemci yapılandırmanıza ekleyin (stdio):

```json
{
  "mcpServers": {
    "tff": {
      "command": "uvx",
      "args": ["tff-mcp==0.1.0"]
    }
  }
}
```

Veya yerelde çalıştırın: `python -m tff_mcp.server` (`mcp<2`, `curl-cffi` gerekir).

## Araçlar

| Araç | Açıklama |
|------|-------------|
| `tff_list_leagues` | Kapsanan 18 lig (slug, Türkçe ad, TFF sayfa kimliği, çok gruplu bilgisi, gol krallığı sayfası var mı) |
| `tff_standings` | Puan cetveli — `league` slug (varsayılan "trendyol-super-lig"); çok gruplu liglerde `group`: sıra ("0"), grup kimliği veya ad ("Kırmızı", "Beyaz", "01"); sıra, takım, oynanan/galibiyet/beraberlik/mağlubiyet, atılan/yenilen gol, averaj, puan |
| `tff_fixtures` | Fikstür ve sonuçlar — `league` slug; `week` ile tek haftaya filtre; çok gruplu liglerde `group`; ev sahibi/deplasman, skor (oynanmadıysa null), durum ("played"/"scheduled"), TFF maç kimliği ve maç detay URL'si |
| `tff_match_detail` | Bir maçın tam detayı — `mac_id` (`tff_fixtures`'ın döndürdüğü, örn. "317874"); takımlar ve skor, tarih/saat, stadyum, lig/sezon, maç kodu, hakem ekibi (hakem, yardımcılar, VAR/AVAR, gözlemci, temsilci), dakikalarıyla goller, iki takımın ilk 11'i |
| `tff_top_scorers` | Gol krallığı — `league`: "trendyol-super-lig" (varsayılan), "trendyol-1-lig", "nesine-2-lig" veya "nesine-3-lig" (gol krallığı sayfası olan dört lig); `limit` 1..50 |

Örnek çıktı (`tff_match_detail` / Gaziantep FK 0–2 Kasımpaşa, 6 Kasım 2026):

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

## Nasıl çalışır

tff.org lig sayfalarını tamamen sunucu taraflı gösterir — giriş, API anahtarı ve çerez gerekmez. Puan cetveli `<table class="s-table">` içindedir (başlık O G B M A Y AV P); fikstür `<table class="fiksturListesiTable">` içindedir ("N.Hafta" başlıkları, ev sahibi kulüp bağlantısı, skor bağlantısı `pageID=29&macId=...` ve deplasman kulüp bağlantısı olan maç satırları — oynanmamış maçlarda " - " yazar). Çok gruplu ligler (Nesine 2. Lig, Nesine 3. Lig, BAL, kadın ve gençlik ligleri) gruplarını `?pageID=<id>&grupID=<n>` bağlantılarıyla gösterir. Maç detaylarında takımlar `lnkTakim1`/`lnkTakim2` içinde, skorlar `MacDetaySayi` span'lerinde, lig/sezon `lblOrganizasyonAdi` içinde, maç kodu `lblKod` içinde, tarih/saat `lblTarih` içinde, stadyum kod ile tarih arasındaki metinde, hakemler `İSİM(ROL)` çiftleri olarak, goller "İSİM,3.dk (F)" biçiminde, ilk 11'ler `grdTakim1/2_rptKadrolar` tekrarlayıcılarındadır. Gol krallığı `rptGolKralligi` tekrarlayıcısından gelir (sayfalar 821/822/823/824). Site windows-1254 kodlamalı eski bir ASP.NET sitesidir, açıkça çözülür. Bir site özelliği uydurulmaz, belgelenir: haftanın hakemleri sayfası (`pageID=600`) 2./3. Lig haftalarını hakem sütunları BOŞ gösterir — atamalar maça yakın açıklanır — bu yüzden hakem verisi maç detay sayfasından alınır. Aktarım Chrome TLS taklidi kullanır (`curl-cffi`, `chrome120`); istekler ~0,8 sn arayla; her şey salt okunurdur.

## Kurulum

```bash
uvx tff-mcp==0.1.0        # doğrudan çalıştır (uv gerekir)
# veya
pip install tff-mcp==0.1.0
tff-mcp    # MCP sunucusunu stdio üzerinde başlatır
```

## Testler

```bash
python -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python -m unittest discover -s tests -v
```

Çevrimdışı testler kayıtlı fiksçırlarla çalışır (gerçek sayfalar 2026-11-09'da çekildi); canlı testler tff.org'a gider. Derleme anında 37/37 yeşil (20 çevrimdışı + 17 canlı) ve bir MCP stdio duman testi.

## Yol haritası

- Disiplin kararları (PFDK/AFDK sayfaları) ve cezalı oyuncular (pageID=633)
- Kulüp sayfaları (pageID=28&kulupID=...) — kadrolar
- Millî takım maçları (pageID=425)

## Lisans

MIT — bkz. [LICENSE](LICENSE).
