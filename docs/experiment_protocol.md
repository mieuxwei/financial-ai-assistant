# Experiment Protocol

Experiments will compare a price/volume/technical baseline with an otherwise matched model that also includes news-sentiment features. Time-aware splits and leakage controls are required.

M3 market snapshots are ordered by ticker and trading date and include a deterministic SHA-256. Research configurations must record the snapshot checksum, provider, requested range, and canonical universe. `ingested_at` is intentionally excluded from the checksum because it is operational metadata rather than market information.

Yahoo raw OHLC values are normalized to six decimal places and its derived adjusted close to three decimal places. Existing adjusted-close changes of `0.005` or less retain the stored value; larger changes create a new dataset revision. This rule is part of snapshot schema `market-prices-v1`.

Potential weekday gaps must not automatically be forward-filled. They require exchange-calendar verification before feature or label generation.
