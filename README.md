# LocaleTripwire

LocaleTripwire is a small open-source project for detecting ambiguous JSON object keys before they enter translation catalogs, configuration files, or API fixtures.

The first planned check covers exact duplicate keys and collisions under Unicode normalization and case conversion, including Turkish dotted/dotless I. The tool is intentionally read-only and offline. Implementation and tests are being prepared in the first feature pull request.

The project is licensed under MIT. See [LICENSE](LICENSE).
