从视频转写中提取细粒度地点候选，输出 JSON `places`。每项必须有 `raw_name`、`name`、`suggested_name`、`city_hint`、`province_hint`、`place_type`、`reason`、`quote`、`segment_ids`、`confidence`。`place_type` 只能从 RESTAURANT、SCENIC_AREA、NEIGHBORHOOD、PEDESTRIAN_STREET、BUSINESS_DISTRICT、MARKET、PARK、MUSEUM、TEMPLE、VILLAGE、TOWN、LANDMARK、ACCOMMODATION、TRANSIT、OTHER 选择。

每项同时提供 `feature`、`experience`、`price`、`queue`、`audience`、`warning`、`author_opinion`；没有来源依据的字段留空。没有有效 segment_ids 的候选不得输出。不得生成坐标、地址或 POI ID；高德校名由后续确定性服务完成。
