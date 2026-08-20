从视频转写中提取地点候选，输出 JSON `places`。每项必须有 `name`、`city_hint`、`province_hint`、`place_type`、`reason`、`quote`、`segment_ids`、`confidence`。没有有效 segment_ids 的候选不得输出。不要生成坐标、地址或 POI ID。
