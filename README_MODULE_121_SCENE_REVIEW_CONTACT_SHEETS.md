
# Module 121 Scene Review Contact Sheets

Tạo ảnh contact sheet theo từng tag AI phân loại, để xem nhanh:
- decor có bị dính người không
- CDCR có bị lọt qua decor không
- game/family/vow/party có đúng không
- tag nào bị lệch nhiều

## Chạy

```powershell
$PROJECT="D:\STT Projects\Wedding_Test_001"

python scripts/create_scene_review_contact_sheets_121.py --project "$PROJECT" --max-per-tag 80
```

Nó sẽ mở folder report. Xem các file JPG:
- `decor__count_...jpg`
- `getting_ready__count_...jpg`
- `wedding_game__count_...jpg`
- `party__count_...jpg`
...

CSV:
- `SCENE_REVIEW_SUMMARY.csv`
- `SCENE_REVIEW_ALL_TAGS.csv`

Sau khi xem, gửi tôi tag nào sai nhiều, ví dụ:
- decor đang chứa CDCR
- vow đang chứa game
- church_ceremony đang chứa gì
