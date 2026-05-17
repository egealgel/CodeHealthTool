# CodeHealthTool

Python projeleri için iki basit kontrol yapan küçük bir CLI:

1. **Dead code bulucu** — AST analizi ile hiç çağrılmayan fonksiyon, sınıf ve metotları tespit eder.
2. **Commit kalite analizi** — `fix bug`, `asdf`, `wip` gibi anlamsız commit mesajlarını yakalar.

Bu tool'un fark yarattığı yer: bir paket bağımlılığı olmaması ve commit kalitesini de aynı CLI'da sunması. Kapsamı internal application/service kod tabanları — Flask/Django uygulamaları, CLI'lar, mikroservisler, dahili scriptler. Yani public API'si olmayan, "kendisini kendisi çağıran" kod tabanları.


## Kurulum

```bash
python -m venv .venv
.venv/bin/pip install -e ".[test]"
```

> Python 3.14 + setuptools editable install kombinasyonunda `codehealth` script entry-point çözülmeyebilir (`__editable__.*.pth` dosyaları Python 3.14'te "gizli" sayılıyor). Geçici çözüm: `python -m codehealth ...` veya `PYTHONPATH=src` ile çalıştırın.

## Kullanım

```bash
# Hiç çağrılmayan fonksiyon ve sınıflar
python -m codehealth deadcode path/to/project

# Son 100 commit mesajını incele
python -m codehealth commits path/to/repo

# Her ikisi birden
python -m codehealth all path/to/project -n 50

# JSON çıktısı (CI için)
python -m codehealth all path/to/project --json
```

Genel bayraklar:

| Bayrak | Açıklama |
|--------|----------|
| `--json` | Düz metin yerine JSON çıktı |
| `--fail-on-warn` | Uyarılar da non-zero exit code üretir |
| `-n / --limit` | İncelenecek commit sayısı (commits/all için, varsayılan 100) |

## Çıktı örnekleri

```text
$ python -m codehealth deadcode src/
[DEAD] src/foo/utils.py:42  function `unused_helper`
[DEAD] src/foo/models.py:88 class `LegacyAdapter`
[MAYBE] src/foo/plugins.py:15  function `register_plugin` (decorated)

2 dead, 1 maybe
```

```text
$ python -m codehealth commits .
[BAD] a1b2c3d  "fix bug"            — generic/meaningless commit message
[BAD] e4f5g6h  "asdf"               — generic/meaningless commit message
[WARN] i7j8k9l "Updated readme"     — 'Updated' is not imperative mood

2 bad / 1 warn / 50 commits  (score: 0.04)
```

## Çıkış kodları

| Kod | Anlam |
|-----|-------|
| 0 | Temiz |
| 1 | Bad bulgu var, ya da `--fail-on-warn` aktifken warn var |
| 2 | Kullanım/argüman hatası |
| 3 | Git çağrısı başarısız (repo yok, git PATH'te yok, vs.) |

## Dead code algoritması

İki geçişli AST taraması:

1. Tüm `.py` dosyalarındaki `FunctionDef`, `AsyncFunctionDef`, `ClassDef` tanımları toplanır.
2. Aynı dosyalarda `Name`, `Attribute`, `Call`, `Import`, `ImportFrom` üzerinden referans isimleri toplanır.
3. Bir tanım, adı hiçbir referans olarak görünmüyorsa **DEAD**; aksi halde göz ardı edilir.

False-positive azaltıcılar:

- **Dunder metotlar** (`__init__`, `__repr__`, `__enter__`, ...) Python tarafından implicit çağrılır.
- **`__all__`** içindeki isimler public API kabul edilir.
- **`test_*` fonksiyonları ve `Test*` sınıfları** test runner tarafından çağrılır.
- **`@dataclass`, `@property`, `@staticmethod`, `@classmethod`, `@abstractmethod`, `@cached_property`, `@lru_cache`, `@wraps`, `@final`, ...** gibi *çağrı semantiğini değiştirmeyen* dekoratörler güvenli sayılır.
- **Kayıt edici dekoratörler** (örn. `@app.route(...)`, `@register(...)`) saptanırsa tanım **MAYBE** olarak işaretlenir.
- **`ast.NodeVisitor` / `*Handler` / `*Dispatcher` / `*Transformer` alt sınıflarındaki** `visit_*`, `do_*`, `handle_*`, `p_*` metotları dinamik dispatch olarak kabul edilir.
- **String-form type annotation'lar** (`def f(x: "MyClass")` veya `from __future__ import annotations` ile) gerçek referans olarak parse edilir.

### Bilinen sınırlamalar

- `getattr(self, name)()`, `globals()[name]()`, `eval`/`exec` ile çağrı yapılan kodlar yakalanamaz → yanlış pozitif olabilir.
- Modül-arası override'lar best-effort: isim eşleşmesi temeli kullanılır.
- `if TYPE_CHECKING:` blokları normal import gibi işlenir; bu genelde doğru sonuç verir.
- `.codehealthignore` desteği yok (yol haritasında).

## Commit kalite kuralları

| Kural | Şiddet |
|-------|--------|
| Subject `< 8` karakter | bad |
| Blacklist isabet (`fix`, `wip`, `update`, `asdf`, `stuff`, ...) | bad |
| Tüm kelimeler blacklist içinde (`wip wip wip`) | bad |
| Tek tekrar eden karakter (`...`, `aaaa`) | bad |
| Tek kelimelik mesaj | warn |
| `> %50` harf-dışı karakter | warn |
| Non-imperative başlangıç (`Fixing`, `Updated`) | warn |
| `Merge ...` / `Revert ...` otomatik mesajları | atlanır |

Skor = (en az bir BAD bulgusu olan commit'ler) / toplam commit.

## Geliştirme

```bash
.venv/bin/pytest -q          # 28 test, hepsi yeşil olmalı
python -m codehealth deadcode src    # tool kendini kontrol eder
```

Proje yapısı:

```
src/codehealth/
  cli.py                       # argparse, alt komutlar
  analyzers/
    dead_code.py               # iki geçişli AST analizi
    commit_quality.py          # kural motoru
  reporters/
    text.py                    # terminal çıktısı
    json_reporter.py           # --json çıktısı
  utils/git.py                 # git log sarmalayıcısı
tests/
  fixtures/
    dead_code_sample/          # basit ölü/canlı kod
    complex_sample/            # dataclass, NodeVisitor, decoratorlü kayıt, string annotation
    commits_sample.txt
    commits_complex.txt        # conventional commits, emoji, wip-zinciri
  test_dead_code.py
  test_dead_code_complex.py
  test_commit_quality.py
  test_commit_quality_complex.py
```

## Lisans

MIT
