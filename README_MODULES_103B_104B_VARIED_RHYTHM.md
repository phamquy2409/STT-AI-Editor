# 103B-104B Varied Rhythm Export

Fix lỗi nhịp source gần bằng nhau.

## Chạy

```powershell
$PROJECT="D:\STT Projects\Wedding_Test_001"
$PROFILE="intimate_7_8min"

python scripts/create_cinematic_varied_rhythm_103b.py --project "$PROJECT" --style-profile "$PROFILE" --target-seconds 480 --target-shots 180 --beat-snap soft

python scripts/export_preserve_varied_rhythm_xml_104b.py --project "$PROJECT" --style-profile "$PROFILE" --preset horizontal_4k --fps 30 --preserve-unknown-duration
```

Import file:

```text
D:\STT Projects\Wedding_Test_001\stt_varied_rhythm_premiere_import.xml
```

Xem output `duration_stats`:
- cần `min` thấp
- `max` cao hơn rõ
- có `under_0_7s`
- có `over_3s`, `over_5s`
