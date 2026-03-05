"""
Mock 数据模块：开发环境模拟 MCP 工具的返回结果。

职责：
    为每种 MCP 工具提供本地模拟数据，确保无需后端服务即可完成开发和演示。

设计思路：
    - 每个工具对应一个 _mock_xxx 函数，返回符合业务格式的模拟数据。
    - 通过 _HANDLERS 字典统一分发。
    - 模拟数据尽量贴近真实场景（城市名动态替换、UUID 生成唯一标识等）。

与其他模块的关系：
    - 仅被 mcp/client.py 的 _mock_call 方法调用。
    - 仅在 development 环境且未配置 mcp_auth_token 时生效。
"""

from __future__ import annotations

import time
import uuid
from typing import Any
from loguru import logger


def get_mock_response(tool_name: str, params: dict[str, Any]) -> Any:
    """根据工具名称返回对应的模拟数据。

    Args:
        tool_name: MCP 工具名称。
        params: 工具调用参数。

    Returns:
        Any: 模拟的返回数据。未匹配到 handler 时返回通用响应。
    """
    handler = _HANDLERS.get(tool_name)
    if handler:
        logger.debug(f"[MockData] 生成模拟数据: {tool_name}")
        return handler(params)
    logger.warning(f"[MockData] 未匹配到 handler: {tool_name}")
    return {"status": "ok", "message": f"Mock response for {tool_name}"}


def _mock_travel_apply(params: dict) -> dict:
    """模拟提交出差申请，返回申请单号。

    Args:
        params: 包含 user_id、destination、start_date、end_date、reason 等申请参数。

    Returns:
        dict: 包含 apply_id 和初始状态。
    """
    _USER_NAMES = {
        "default_user": "刘洋",
        "ws_user": "刘洋",
    }

    start = params.get("start_date", "2026-03-10")
    end = params.get("end_date", "2026-03-12")
    date_range = f"{start} ~ {end}"

    user_id = params.get("user_id", "申请人")
    applicant = _USER_NAMES.get(user_id, user_id)

    return {
        "apply_id": "TA-20260303-001",
        "status": "pending",
        "message": "出差申请已提交，等待审批",
        "applicant": applicant,
        "destination": params.get("destination", "上海"),
        "date_range": date_range,
        "reason": params.get("reason", "出差"),
        "submitted_at": "2026-03-03 10:30",
        "timeline": [
            {"step": "提交申请", "status": "done", "time": "03-03 10:30"},
            {"step": "部门审批", "status": "current", "time": ""},
            {"step": "审批完成", "status": "upcoming", "time": ""},
        ],
    }


def _mock_travel_status(params: dict) -> dict:
    """模拟查询出差申请状态（默认返回已通过）。

    Args:
        params: 包含 apply_id。

    Returns:
        dict: 包含审批状态和审批人信息。
    """
    return {
        "apply_id": params.get("apply_id", "TA-20260303-001"),
        "status": "approved",
        "applicant": "刘洋",
        "destination": "上海",
        "date_range": "2026-03-10 ~ 2026-03-12",
        "reason": "客户拜访",
        "approver": "张经理",
        "submitted_at": "2026-03-03 10:30",
        "approved_at": "2026-03-03 14:15",
        "timeline": [
            {"step": "提交申请", "status": "done", "time": "03-03 10:30"},
            {"step": "部门审批", "status": "done", "time": "03-03 14:15"},
            {"step": "审批通过", "status": "done", "time": "03-03 14:15"},
        ],
    }


def _mock_hotel_list(params: dict) -> list[dict]:
    """模拟酒店列表查询，根据城市名动态生成 5 家酒店。

    Args:
        params: 包含 city、check_in、check_out。

    Returns:
        list[dict]: 酒店信息列表。
    """
    city = params.get("city", "上海")
    return [
        {
            "hotel_id": "H001",
            "name": "浦东丽思卡尔顿",
            "address": f"{city}市陆家嘴世纪大道8号",
            "price_per_night": 1880.0,
            "rating": 4.9,
            "stars": 5,
            "room_type": "商务套房",
            "breakfast_included": True,
            "cancellation_policy": "入住前24小时免费取消",
            "image_url": "https://example.com/hotels/ritz-carlton.jpg",
            "tags": ["商务优选", "含早", "行政酒廊"],
            "amenities": ["WiFi", "早餐", "健身房", "泳池", "商务中心", "行政酒廊"],
            "distance_to_destination": "0.5km",
        },
        {
            "hotel_id": "H002",
            "name": "外滩华尔道夫",
            "address": f"{city}市中山东一路2号",
            "price_per_night": 1580.0,
            "rating": 4.8,
            "stars": 5,
            "room_type": "豪华大床房",
            "breakfast_included": True,
            "cancellation_policy": "入住前48小时免费取消",
            "image_url": "https://example.com/hotels/waldorf.jpg",
            "tags": ["江景", "含早", "历史建筑"],
            "amenities": ["WiFi", "早餐", "健身房", "SPA", "江景房"],
            "distance_to_destination": "1.2km",
        },
        {
            "hotel_id": "H003",
            "name": "陆家嘴香格里拉",
            "address": f"{city}市浦东新区富城路33号",
            "price_per_night": 1280.0,
            "rating": 4.7,
            "stars": 5,
            "room_type": "高级房",
            "breakfast_included": True,
            "cancellation_policy": "入住前24小时免费取消",
            "image_url": "https://example.com/hotels/shangri-la.jpg",
            "tags": ["商务优选", "含早", "地铁直达"],
            "amenities": ["WiFi", "早餐", "健身房", "泳池", "商务中心"],
            "distance_to_destination": "0.8km",
        },
        {
            "hotel_id": "H004",
            "name": "虹桥雅高美爵",
            "address": f"{city}市闵行区申虹路666号",
            "price_per_night": 680.0,
            "rating": 4.5,
            "stars": 4,
            "room_type": "商务大床房",
            "breakfast_included": True,
            "cancellation_policy": "入住前18小时免费取消",
            "image_url": "https://example.com/hotels/novotel.jpg",
            "tags": ["商务优选", "含早", "近机场"],
            "amenities": ["WiFi", "早餐", "健身房", "商务中心"],
            "distance_to_destination": "2.1km",
        },
        {
            "hotel_id": "H005",
            "name": "虹桥全季酒店",
            "address": f"{city}市闵行区虹桥商务区申长路1688号",
            "price_per_night": 458.0,
            "rating": 4.3,
            "stars": 3,
            "room_type": "标准双床房",
            "breakfast_included": True,
            "cancellation_policy": "入住前12小时免费取消",
            "image_url": "https://example.com/hotels/hanting.jpg",
            "tags": ["经济实惠", "含早", "近高铁站"],
            "amenities": ["WiFi", "早餐", "洗衣服务"],
            "distance_to_destination": "3.5km",
        },
    ]


def _mock_flights(params: dict) -> list[dict]:
    """模拟航班列表查询，生成 5 个航班选项。

    Args:
        params: 包含 origin、destination、date。

    Returns:
        list[dict]: 航班信息列表。
    """
    origin = params.get("origin", "北京")
    dest = params.get("destination", "上海")
    date = params.get("date", "2026-03-10")
    return [
        {
            "flight_id": "F001",
            "airline": "中国国航",
            "flight_no": "CA1501",
            "origin": origin,
            "destination": dest,
            "depart_time": f"{date} 07:30",
            "arrive_time": f"{date} 09:45",
            "price": 1280.0,
            "cabin_class": "经济舱",
            "remaining_seats": 23,
            "aircraft_type": "波音737-800",
            "on_time_rate": "92%",
            "meal_included": True,
            "baggage_allowance": "20kg",
            "tags": ["早班机", "含餐", "准点率高"],
        },
        {
            "flight_id": "F002",
            "airline": "东方航空",
            "flight_no": "MU5101",
            "origin": origin,
            "destination": dest,
            "depart_time": f"{date} 09:00",
            "arrive_time": f"{date} 11:15",
            "price": 1150.0,
            "cabin_class": "经济舱",
            "remaining_seats": 18,
            "aircraft_type": "空客A320",
            "on_time_rate": "89%",
            "meal_included": True,
            "baggage_allowance": "20kg",
            "tags": ["含餐", "东航精品线"],
        },
        {
            "flight_id": "F003",
            "airline": "中国南航",
            "flight_no": "CZ3101",
            "origin": origin,
            "destination": dest,
            "depart_time": f"{date} 12:30",
            "arrive_time": f"{date} 14:50",
            "price": 1080.0,
            "cabin_class": "经济舱",
            "remaining_seats": 12,
            "aircraft_type": "波音737MAX",
            "on_time_rate": "91%",
            "meal_included": True,
            "baggage_allowance": "20kg",
            "tags": ["含餐", "准点率高"],
        },
        {
            "flight_id": "F004",
            "airline": "海南航空",
            "flight_no": "HU7801",
            "origin": origin,
            "destination": dest,
            "depart_time": f"{date} 15:00",
            "arrive_time": f"{date} 17:20",
            "price": 980.0,
            "cabin_class": "经济舱",
            "remaining_seats": 31,
            "aircraft_type": "空客A321",
            "on_time_rate": "88%",
            "meal_included": True,
            "baggage_allowance": "20kg",
            "tags": ["特惠", "含餐"],
        },
        {
            "flight_id": "F005",
            "airline": "中国国航",
            "flight_no": "CA1505",
            "origin": origin,
            "destination": dest,
            "depart_time": f"{date} 18:30",
            "arrive_time": f"{date} 20:50",
            "price": 2580.0,
            "cabin_class": "商务舱",
            "remaining_seats": 4,
            "aircraft_type": "空客A330",
            "on_time_rate": "94%",
            "meal_included": True,
            "baggage_allowance": "32kg",
            "tags": ["商务舱", "含餐", "准点率高", "宽体机"],
        },
    ]


def _mock_trains(params: dict) -> list[dict]:
    """模拟高铁车次列表查询，生成 5 个车次选项。

    Args:
        params: 包含 origin、destination、date。

    Returns:
        list[dict]: 高铁车次信息列表。
    """
    origin = params.get("origin", "北京")
    dest = params.get("destination", "上海")
    date = params.get("date", "2026-03-10")
    origin_station = f"{origin}南站" if "北京" in str(origin) else (f"{origin}虹桥站" if "上海" in str(origin) else f"{origin}站")
    dest_station = f"{dest}虹桥站" if "上海" in str(dest) else (f"{dest}南站" if "北京" in str(dest) else f"{dest}站")
    return [
        {
            "train_id": "T001",
            "train_no": "G1",
            "origin": origin_station,
            "destination": dest_station,
            "depart_time": f"{date} 06:36",
            "arrive_time": f"{date} 10:28",
            "duration": "3小时52分",
            "price": 553.0,
            "seat_type": "二等座",
            "remaining_seats": 156,
            "train_type": "复兴号",
            "wifi_available": True,
            "power_outlet": True,
            "tags": ["最快", "WiFi", "复兴号"],
        },
        {
            "train_id": "T002",
            "train_no": "G3",
            "origin": origin_station,
            "destination": dest_station,
            "depart_time": f"{date} 07:00",
            "arrive_time": f"{date} 11:23",
            "duration": "4小时23分",
            "price": 553.0,
            "seat_type": "二等座",
            "remaining_seats": 89,
            "train_type": "复兴号",
            "wifi_available": True,
            "power_outlet": True,
            "tags": ["WiFi", "复兴号"],
        },
        {
            "train_id": "T003",
            "train_no": "G7",
            "origin": origin_station,
            "destination": dest_station,
            "depart_time": f"{date} 09:00",
            "arrive_time": f"{date} 13:48",
            "duration": "4小时48分",
            "price": 553.0,
            "seat_type": "二等座",
            "remaining_seats": 42,
            "train_type": "和谐号",
            "wifi_available": False,
            "power_outlet": True,
            "tags": ["经济实惠"],
        },
        {
            "train_id": "T004",
            "train_no": "G5",
            "origin": origin_station,
            "destination": dest_station,
            "depart_time": f"{date} 14:00",
            "arrive_time": f"{date} 18:28",
            "duration": "4小时28分",
            "price": 933.0,
            "seat_type": "一等座",
            "remaining_seats": 12,
            "train_type": "复兴号",
            "wifi_available": True,
            "power_outlet": True,
            "tags": ["一等座", "WiFi", "复兴号"],
        },
        {
            "train_id": "T005",
            "train_no": "G19",
            "origin": origin_station,
            "destination": dest_station,
            "depart_time": f"{date} 17:00",
            "arrive_time": f"{date} 21:16",
            "duration": "4小时16分",
            "price": 1748.0,
            "seat_type": "商务座",
            "remaining_seats": 3,
            "train_type": "复兴号",
            "wifi_available": True,
            "power_outlet": True,
            "tags": ["商务座", "WiFi", "复兴号", "舒适"],
        },
    ]


def _mock_book(params: dict) -> dict:
    """模拟预订操作，返回订单号（通用兜底）。

    Args:
        params: 包含 booking_id、user_id 等预订参数。

    Returns:
        dict: 包含 order_id 和确认状态。
    """
    return {
        "order_id": f"ORD-XX-{int(time.time())}",
        "status": "confirmed",
        "message": "预订成功",
        "booking_type": "unknown",
        "total_price": 0,
        "details": {},
    }


def _mock_book_flight(params: dict) -> dict:
    """模拟机票预订，返回订单详情。"""
    price = params.get("price", 1280)
    flight_no = params.get("flight_no", "CA1501")
    code = f"FLT-{int(time.time())}-{uuid.uuid4().hex[:6].upper()}"
    return {
        "order_id": f"ORD-XX-{int(time.time())}",
        "status": "confirmed",
        "message": "机票预订成功",
        "booking_type": "flight",
        "total_price": price,
        "confirmation_code": code,
        "payment_deadline": "请在30分钟内完成支付",
        "contact_phone": "400-820-0999",
        "details": {
            "航班号": flight_no,
            "舱位": params.get("cabin_class", "经济舱"),
            "出发时间": params.get("depart_time", ""),
            "到达时间": params.get("arrive_time", ""),
        },
    }


def _mock_book_hotel(params: dict) -> dict:
    """模拟酒店预订，返回订单详情。"""
    price = params.get("price_per_night", 1680)
    nights = params.get("nights", 1)
    total = price * nights
    code = f"HTL-{int(time.time())}-{uuid.uuid4().hex[:6].upper()}"
    return {
        "order_id": f"ORD-XX-{int(time.time())}",
        "status": "confirmed",
        "message": "酒店预订成功",
        "booking_type": "hotel",
        "total_price": total,
        "confirmation_code": code,
        "payment_deadline": "请在30分钟内完成支付",
        "contact_phone": "400-820-0999",
        "details": {
            "酒店名称": params.get("hotel_name", "浦东丽思卡尔顿"),
            "入住日期": params.get("check_in", ""),
            "退房日期": params.get("check_out", ""),
            "入住晚数": nights,
        },
    }


def _mock_book_train(params: dict) -> dict:
    """模拟火车票预订，返回订单详情。"""
    price = params.get("price", 553)
    code = f"TRN-{int(time.time())}-{uuid.uuid4().hex[:6].upper()}"
    return {
        "order_id": f"ORD-XX-{int(time.time())}",
        "status": "confirmed",
        "message": "火车票预订成功",
        "booking_type": "train",
        "total_price": price,
        "confirmation_code": code,
        "payment_deadline": "请在30分钟内完成支付",
        "contact_phone": "12306",
        "details": {
            "车次": params.get("train_no", "G1"),
            "座位类型": params.get("seat_type", "二等座"),
            "出发时间": params.get("depart_time", ""),
            "到达时间": params.get("arrive_time", ""),
        },
    }


_HANDLERS = {
    "travel_apply": _mock_travel_apply,
    "travel_apply_status": _mock_travel_status,
    "get_hotel_list": _mock_hotel_list,
    "get_hotel_detail": lambda p: _mock_hotel_list(p)[0] if _mock_hotel_list(p) else {},
    "get_flights": _mock_flights,
    "get_trains": _mock_trains,
    "book_hotel": _mock_book_hotel,
    "book_flight": _mock_book_flight,
    "book_train": _mock_book_train,
}
