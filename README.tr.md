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
```

Örnek JSON:

```json
{"ISIK": "ışık", "ısık": "başka değer"}
```

Bu çift `tr-lower` kuralıyla işaretlenir. `{"Name": 1, "name": 2}` ise `casefold` kuralıyla yakalanır. `café` sözcüğünün birleşik ve ayrışık Unicode yazımları `nfc` kuralına takılır. Aynı çift birden fazla kuralda görünebilir.

Çıkış kodları: `0` bulgu yok, `1` çakışma var, `2` dosya okunamadı veya JSON geçersiz. `--format json` çıktısı `findings` ve `errors` alanlarını içerir; CI için uygundur. Raporlanan yol, dizi indeksleri dâhil, anahtarların bulunduğu JSON nesnesini gösterir.

## Bulguyu nasıl yorumlamalı?

JSON anahtarları normalde ancak birebir aynıysa eşit kabul edilir. Dolayısıyla birebir tekrar dışındaki bulgular, belirli bir uygulamada kesin hata olduğu anlamına gelmez; **olası uyumluluk riski** gösterir. Araç tüm CLDR dil kurallarını, benzer görünümlü karakterleri, JSON Schema'yı veya çeviri kalitesini denetlemez. Türkçe kuralı özellikle `I/İ/ı/i` dönüşümüne odaklanan bir kestirimdir.

Dosyalar yalnızca yerelde okunur, hiçbir servise gönderilmez. Issue açarken özel çeviri dosyası veya API verisi paylaşmayın; küçük ve yapay bir örnek kullanın.

## Geliştirme ve katkı

```sh
python3 -m unittest discover -s tests -v
```

Katkı için örnek JSON'u, etkilenen yazılımı ve beklenen davranışı anlatan bir issue açabilirsiniz. Yanlış alarmları azaltan veya gerçek kullanım örneklerini belgeleyen katkılar özellikle değerli.

MIT lisanslıdır; [LICENSE](LICENSE) dosyasına bakın.
