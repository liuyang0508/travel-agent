"""
差旅业务模型模块：定义出差申请、行程、酒店、机票、高铁等领域对象。

职责：
    提供差旅业务的核心数据结构，供 API 层序列化和 Agent 层传递使用。

核心概念：
    - TravelApply：出差申请单，包含目的地、日期、事由和审批状态。
    - Itinerary：行程信息，关联申请单并描述交通和住宿偏好。
    - HotelInfo / FlightInfo / TrainInfo：资源查询结果的结构化表示。
    - TravelPlan：综合差旅方案，汇总行程和推荐资源。

与其他模块的关系：
    - 被 mcp/tools/mock_data 的返回值格式参考。
    - 被 api 层用于请求/响应的类型定义。
    - 与 agents/state.TravelContext 互补：TravelContext 是运行时状态，
      本模块中的模型是持久化和传输的数据结构。
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from pydantic import BaseModel, Field


class TravelApplyStatus(str, Enum):
    """出差申请审批状态枚举。"""
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class TransportType(str, Enum):
    """交通方式枚举。"""
    FLIGHT = "flight"
    TRAIN = "train"
    OTHER = "other"


class TravelApply(BaseModel):
    """出差申请单。

    Attributes:
        apply_id: 申请单号（由后端生成）。
        user_id: 申请人 ID。
        reason: 出差事由。
        destination: 目的城市。
        origin: 出发城市。
        start_date: 出发日期。
        end_date: 返回日期。
        status: 审批状态。
        created_at: 创建时间。
    """
    apply_id: str | None = None
    user_id: str
    reason: str
    destination: str
    origin: str = ""
    start_date: date
    end_date: date
    status: TravelApplyStatus = TravelApplyStatus.DRAFT
    created_at: datetime = Field(default_factory=datetime.now)


class Itinerary(BaseModel):
    """行程信息，描述一次出差的交通和住宿需求。

    Attributes:
        apply_id: 关联的出差申请单号。
        origin: 出发城市。
        destination: 目的城市。
        depart_date: 出发日期。
        return_date: 返回日期。
        transport_type: 首选交通方式。
        hotel_preferences: 酒店偏好标签列表。
        budget_limit: 预算上限（可选）。
    """
    apply_id: str
    origin: str
    destination: str
    depart_date: date
    return_date: date
    transport_type: TransportType = TransportType.FLIGHT
    hotel_preferences: list[str] = Field(default_factory=list)
    budget_limit: float | None = None


class HotelInfo(BaseModel):
    """酒店信息。

    Attributes:
        hotel_id: 酒店唯一 ID。
        name: 酒店名称。
        address: 酒店地址。
        price_per_night: 每晚价格（元）。
        rating: 评分（0.0~5.0）。
        amenities: 设施标签列表。
        distance_to_destination: 到目的地的距离描述。
    """
    hotel_id: str
    name: str
    address: str
    price_per_night: float
    rating: float = 0.0
    amenities: list[str] = Field(default_factory=list)
    distance_to_destination: str = ""


class FlightInfo(BaseModel):
    """航班信息。

    Attributes:
        flight_id: 航班唯一 ID。
        airline: 航空公司名称。
        flight_no: 航班号。
        origin: 出发城市。
        destination: 目的城市。
        depart_time: 起飞时间。
        arrive_time: 到达时间。
        price: 票价（元）。
        cabin_class: 舱位等级。
        remaining_seats: 余票数。
    """
    flight_id: str
    airline: str
    flight_no: str
    origin: str
    destination: str
    depart_time: datetime
    arrive_time: datetime
    price: float
    cabin_class: str = "economy"
    remaining_seats: int = 0


class TrainInfo(BaseModel):
    """高铁车次信息。

    Attributes:
        train_id: 车次唯一 ID。
        train_no: 车次号。
        origin: 出发城市。
        destination: 目的城市。
        depart_time: 发车时间。
        arrive_time: 到达时间。
        price: 票价（元）。
        seat_type: 座位类型。
        remaining_seats: 余票数。
    """
    train_id: str
    train_no: str
    origin: str
    destination: str
    depart_time: datetime
    arrive_time: datetime
    price: float
    seat_type: str = "二等座"
    remaining_seats: int = 0


class TravelPlan(BaseModel):
    """综合差旅方案，汇总行程信息和推荐资源。

    Attributes:
        apply_id: 关联的出差申请单号。
        itinerary: 行程信息。
        recommended_hotels: 推荐酒店列表。
        recommended_flights: 推荐航班列表。
        recommended_trains: 推荐高铁列表。
        total_estimated_cost: 总预估费用（元）。
        summary: LLM 生成的方案摘要文本。
    """
    apply_id: str
    itinerary: Itinerary
    recommended_hotels: list[HotelInfo] = Field(default_factory=list)
    recommended_flights: list[FlightInfo] = Field(default_factory=list)
    recommended_trains: list[TrainInfo] = Field(default_factory=list)
    total_estimated_cost: float = 0.0
    summary: str = ""
