# LocaleTripwire

[English README](README.md)

LocaleTripwire, UTF-8 JSON dosyalarındaki belirsiz anahtarları bulan küçük ve çevrimdışı bir komut satırı aracıdır. Birebir yinelenen anahtarları; Unicode NFC normalizasyonu, büyük/küçük harf eşleştirmesi (`casefold`) veya odaklı Türkçe küçük harf dönüşümü sonrasında çakışan çiftleri raporlar. Anahtarların bulunduğu nesnenin yolunu gösterir; dosyaları değiştirmez.

Sorun somut: [yinelenen anahtarlar çeviri dosyasının içe aktarımını bozabiliyor](https://opswat.developerhub.io/docs/mdmft/v3.11.3/knowledge-base/why-do-i-receive--localization-file-has-xxx-keys-but-your-transl). [Unicode normalizasyonu](https://unicode.org/faq/normalization.html) ve [Türkçe harf dönüşümü](https://github.com/jeancroy/fuzz-aldrin-plus/issues/33) de farklı sistemlerde beklenmedik karşılaştırmalara yol açabiliyor. Bu proje, [li18nt](https://github.com/simonwep/li18nt) gibi genel çeviri denetçilerinin yerine geçmeyi değil, dar bir ön kontrol sunmayı amaçlıyor.

## Kurulum

Python 3.10 veya üzeri gerekir. Bu repo içindeyken:

```sh
python3 -m pip install -e .
```

## Kullanım

```sh
locale-tripwire messages.json
locale-tripwire --format json messages.json config.json
locale-tripwire locales/ --exclude generated --exclude 'drafts/*.json'
locale-tripwire locales/ --rules duplicate,nfc --severity nfc=warning
locale-tripwire locales/ --rules casefold --severity casefold=warning --fail-on warning
```

Örnek JSON:

```json
{"ISIK": "ışık", "ısık": "başka değer"}
```

Bu çift `tr-lower` kuralıyla işaretlenir. `{"Name": 1, "name": 2}` ise `casefold` kuralıyla yakalanır. `café` sözcüğünün birleşik ve ayrışık Unicode yazımları `nfc` kuralına takılır. Aynı çift birden fazla kuralda görünebilir.

### Kural seçimi ve uyarı seviyeleri

`--rules`, `duplicate,nfc,casefold,tr-lower` listesinden virgülle ayrılmış kuralları
seçer. Geriye uyumluluk için varsayılan olarak bütün kurallar `error` seviyesindedir.
Tekrarlanabilen `--severity KURAL=warning` veya `KURAL=error` ile etkin kuralların
seviyesini değiştirebilirsiniz. Uyarılar raporlanır ama yalnız `--fail-on warning`
verildiğinde komutu başarısız yapar. JSON anahtarlarını birebir karşılaştıran
uygulamalarda `--rules duplicate` ile başlayın; diğer dönüşümler tüketici uygulamanızda
gerçekten kullanılıyorsa ilgili kuralları açın.

Çıkış kodları: `0` başarısızlık eşiğinde bulgu yok, `1` eşikte bulgu var,
`2` okunamayan/geçersiz girdi (`NaN`/`Infinity` dâhil) veya eşleşen dosya bulunmayan
klasör. Girdi hatası, bulgulara göre önceliklidir. Geçersiz seçenekler de `2` döndürür.

### Açıklayıcı rapor

Her bulguda nesne yolu (ör. `$["items"][0]`), iki anahtarın açılış tırnağının konumu,
Unicode kod noktaları/adları ve dönüşüm sonrasındaki ortak anahtar gösterilir.
Satır ve sütunlar **1 tabanlı karakter konumlarıdır**, bayt konumu değildir.
Kaçış dizisi içeren anahtarlar kaynak metindeki açılış tırnağına işaret eder.
Metin çıktısında ASCII dışı ve kontrol karakterleri kaçırılır; Windows'ta yönlendirilmiş
çıktıda da güvenle okunabilir.

JSON çıktısındaki `findings`, `errors` ve bulguların `file`, `path`, `rule`, `first`,
`second` alanları korunur. Yeni alanlar: `severity`, `first_position`, `second_position`
(`line` ve `column` içerir), `first_codepoints`, `second_codepoints`, `transformed`.

### Klasör tarama

Klasörler alt klasörleriyle, sabit sırada `*.json` dosyaları için taranır.
Tekrarlanan `--include GLOB` seçenekleri varsayılan dosya desenini değiştirir.
`--exclude GLOB` ile dosya/klasör adını veya kök klasöre göre yolu hariç tutabilirsiniz.
Desenleri tırnak içinde yazın. Eşleşme her platformda büyük/küçük harfe duyarlıdır;
yol ayırıcı `/` kullanılır. Python `fnmatch` kuralları geçerlidir, gitignore değildir;
`*`, `/` karakteriyle de eşleşebilir. Hariç tutulan klasörün tamamı atlanır.

Klasör keşfinde `.git`, `node_modules`, `.venv`, `venv`, `__pycache__` ve sembolik
bağlantılar daima atlanır. Aynı dosyaya giden girdiler tekilleştirilir. Doğrudan
verilen dosyalar filtrelerden bağımsız incelenir ve sembolik bağlantı olabilir;
doğrudan verilen klasörler her zaman taranır. Girdi dosyaları değiştirilmez.

## Bulguyu nasıl yorumlamalı?

JSON anahtarları normalde ancak birebir aynıysa eşit kabul edilir. Dolayısıyla birebir tekrar dışındaki bulgular, belirli bir uygulamada kesin hata olduğu anlamına gelmez; **olası uyumluluk riski** gösterir. Araç tüm CLDR dil kurallarını, benzer görünümlü karakterleri, JSON Schema'yı veya çeviri kalitesini denetlemez. Türkçe kuralı özellikle `I/İ/ı/i` dönüşümüne odaklanan bir kestirimdir.

Dosyalar yalnızca yerelde okunur, hiçbir servise gönderilmez. Issue açarken özel çeviri dosyası veya API verisi paylaşmayın; küçük ve yapay bir örnek kullanın.

## Geliştirme ve katkı

```sh
python3 -m unittest discover -s tests -v
```

Katkı için örnek JSON'u, etkilenen yazılımı ve beklenen davranışı anlatan bir issue açabilirsiniz. Yanlış alarmları azaltan veya gerçek kullanım örneklerini belgeleyen katkılar özellikle değerli.

MIT lisanslıdır; [LICENSE](LICENSE) dosyasına bakın.
