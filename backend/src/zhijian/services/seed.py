from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zhijian.db.models import ContentItem, Job, Place, PlaceObservation, RouteDraft, RouteDraftItem, Source
from zhijian.domain.enums import ContentType, JobStatus, JobType, ResolutionStatus, UserState


def seed_demo_data(db: Session) -> None:
    if db.scalar(select(func.count(ContentItem.id))) or 0:
        return

    recruitment_source = Source(
        source_type="URL",
        locator="https://rsj.beijing.gov.cn/example",
        title="北京市事业单位 2025 年公开招聘",
        authority="OFFICIAL",
    )
    travel_source = Source(
        source_type="URL",
        locator="https://www.bilibili.com/video/BV189ui6LEhK",
        title="厦门街头米其林小馆",
        authority="PLATFORM",
    )
    db.add_all([recruitment_source, travel_source])
    db.flush()

    contents = [
        ContentItem(
            content_type=ContentType.RECRUITMENT.value,
            title="北京市事业单位 2025 年公开招聘",
            summary="官方公告已完成结构化，报名时间和学历要求均保留原文依据。",
            source_id=recruitment_source.id,
            structured_json={
                "deadline": "2025-06-03 17:00",
                "position_count": 12,
                "degree": "本科及以上",
                "region": "北京市",
                "eligibility": [
                    {"label": "学历", "value": "本科及以上", "status": "PASS"},
                    {"label": "专业", "value": "计算机类", "status": "PASS"},
                    {"label": "应届身份", "value": "待确认", "status": "REVIEW"},
                    {"label": "户籍", "value": "信息不足", "status": "UNKNOWN"},
                ],
            },
        ),
        ContentItem(
            content_type=ContentType.RECRUITMENT.value,
            title="中国人民银行 2025 年招聘公告",
            summary="招聘公告与岗位条件已提取。",
            source_id=recruitment_source.id,
            structured_json={"deadline": "2025-06-08 18:00", "position_count": 86},
        ),
        ContentItem(
            content_type=ContentType.TRAVEL.value,
            title="贵州黔东南 8 日路线",
            summary="已识别 18 个地点，其中 15 个已确认 POI。",
            source_id=travel_source.id,
            structured_json={"confirmed_places": 15, "review_places": 3},
        ),
        ContentItem(
            content_type=ContentType.TRAVEL.value,
            title="厦门街头米其林小馆",
            summary="沙茶面与海蛎煎，人均约 ¥65，候选地址等待最终确认。",
            source_id=travel_source.id,
            status="NEEDS_USER",
            structured_json={"confirmed_places": 7, "review_places": 1},
        ),
    ]
    db.add_all(contents)
    db.flush()

    places_data = [
        ("厦门街头米其林小馆", "餐馆", 24.4555, 118.0818, "思明区中山路附近", UserState.SAVED.value),
        ("八市海鲜市场", "市场", 24.4612, 118.0782, "思明区开禾路", UserState.PLANNED.value),
        ("沙坡尾艺术西区", "景点", 24.4387, 118.0876, "思明区大学路", UserState.VISITED.value),
        ("南普陀寺", "景点", 24.4431, 118.0966, "思明区思明南路", UserState.DISCOVERED.value),
        ("环岛路海岸", "景点", 24.4323, 118.1128, "思明区环岛南路", UserState.SAVED.value),
        ("植物园钟鼓索道", "景点", 24.4485, 118.1032, "思明区虎园路", UserState.DISCOVERED.value),
        ("鼓浪屿龙头路", "街区", 24.4480, 118.0687, "思明区鼓浪屿", UserState.PLANNED.value),
        ("铁路文化公园", "公园", 24.4540, 118.0989, "思明区文屏路", UserState.DISCOVERED.value),
    ]
    places: list[Place] = []
    for index, (name, place_type, lat, lng, address, state) in enumerate(places_data):
        place = Place(
            content_item_id=contents[3].id,
            name=name,
            place_type=place_type,
            province="福建省",
            city="厦门市",
            district="思明区",
            address=address,
            latitude=lat,
            longitude=lng,
            coordinate_system="GCJ02",
            external_provider="AMap",
            external_poi_id=f"demo-{index + 1}",
            resolution_status=ResolutionStatus.CONFIRMED.value,
            user_state=state,
            summary="适合步行探索，可从原视频时间码回溯地点依据。",
            metadata_json={"price": "约 ¥65" if index == 0 else None},
        )
        db.add(place)
        places.append(place)
    db.flush()
    db.add_all(
        [
            PlaceObservation(
                place_id=places[0].id,
                source_id=travel_source.id,
                observation_type="dish",
                value_json={"value": "沙茶面、海蛎煎", "timestamp": "03:42"},
            ),
            PlaceObservation(
                place_id=places[0].id,
                source_id=travel_source.id,
                observation_type="price",
                value_json={"value": "人均约 ¥65", "timestamp": "05:18"},
            ),
        ]
    )

    route = RouteDraft(name="厦门一日路线", city="厦门市")
    db.add(route)
    db.flush()
    db.add_all(
        [
            RouteDraftItem(route_draft_id=route.id, place_id=places[0].id, sort_order=1),
            RouteDraftItem(route_draft_id=route.id, place_id=places[2].id, sort_order=2),
        ]
    )

    db.add_all(
        [
            Job(
                job_type=JobType.RECRUITMENT.value,
                status=JobStatus.RUNNING.value,
                current_step="EXTRACT",
                progress=72,
                payload_json={"title": "北京市事业单位招聘公告"},
            ),
            Job(
                job_type=JobType.TRAVEL.value,
                status=JobStatus.RUNNING.value,
                current_step="SEGMENT",
                progress=46,
                payload_json={"title": "贵州黔东南 8 日路线"},
            ),
        ]
    )
    db.commit()
