import pytest
from httpx import AsyncClient
from backend.app.ai.agent.travel_agent import TravelAgent, travel_agent
from backend.app.ai.orchestration.intent_detector import IntentDetector, UserIntent
from backend.app.ai.orchestration.orchestrator import TravelOrchestrator
from backend.app.ai.orchestration.tool_selector import ToolSelector
from backend.app.ai.tools.base import DataProvenance, ToolResult
from backend.app.ai.tools.registry import default_tool_registry


EXPECTED_TOOLS = [
    "search_destinations",
    "search_attractions",
    "search_activities",
    "search_hotels",
    "search_restaurants",
    "search_flights",
    "search_airports",
    "search_places",
    "get_place_details",
    "get_weather",
    "calculate_distance",
    "calculate_route",
    "search_local_database",
    "get_user_preferences",
    "create_itinerary",
    "save_trip",
    "retrieve_trip",
]


def test_tool_registry_contains_all_17_tools():
    """Verify all 17 required travel tools are registered and have valid function calling schemas."""
    for tool_name in EXPECTED_TOOLS:
        tool = default_tool_registry.get(tool_name)
        assert tool is not None, f"Tool '{tool_name}' not found in default_tool_registry."
        assert tool.name == tool_name
        assert tool.description
        assert isinstance(tool.parameters, dict)

        # Validate schema contract
        schema = tool.get_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == tool_name
        assert "description" in schema["function"]
        assert "parameters" in schema["function"]


def test_intent_detection_user_examples():
    """Verify intent detector accurately classifies queries matching all user prompt examples."""
    detector = IntentDetector()

    # Example 1: "Best places to visit in India?"
    res1 = detector.detect("Best places to visit in India?")
    assert res1.intent == UserIntent.DESTINATION_DISCOVERY
    assert "search_destinations" in res1.required_tools

    # Example 2: "Find hotels in Jaipur."
    res2 = detector.detect("Find hotels in Jaipur.")
    assert res2.intent == UserIntent.HOTEL_SEARCH
    assert "search_hotels" in res2.required_tools
    assert "search_places" in res2.required_tools

    # Example 3: "Plan a 5-day Rajasthan trip."
    res3 = detector.detect("Plan a 5-day Rajasthan trip.")
    assert res3.intent == UserIntent.ITINERARY_PLANNING
    expected_planning_tools = [
        "search_destinations",
        "search_attractions",
        "search_activities",
        "search_hotels",
        "calculate_distance",
        "create_itinerary",
    ]
    for t in expected_planning_tools:
        assert t in res3.required_tools, f"Expected '{t}' in required_tools for itinerary planning."
    assert res3.entities.get("days") == 5

    # Example 4: "Find me flights from Kolkata to Delhi."
    res4 = detector.detect("Find me flights from Kolkata to Delhi.")
    assert res4.intent == UserIntent.FLIGHT_SEARCH
    assert "search_flights" in res4.required_tools
    assert res4.entities.get("origin") == "Kolkata"
    assert res4.entities.get("destination") == "Delhi"


def test_tool_selector_resolution():
    """Verify ToolSelector binds appropriate arguments from detected entities."""
    detector = IntentDetector()
    selector = ToolSelector()

    analysis = detector.detect("Find me flights from Kolkata to Delhi.")
    calls = selector.resolve_tool_calls(analysis, "Find me flights from Kolkata to Delhi.")
    assert len(calls) == 1
    assert calls[0]["tool_name"] == "search_flights"
    assert calls[0]["kwargs"]["origin"] == "Kolkata"
    assert calls[0]["kwargs"]["destination"] == "Delhi"


@pytest.mark.asyncio
async def test_distance_and_route_tools():
    """Verify calculate_distance and calculate_route calculate realistic distances and transit times."""
    dist_tool = default_tool_registry.get("calculate_distance")
    assert dist_tool is not None

    res = await dist_tool.execute(origin="Jaipur", destination="Jodhpur")
    assert res.success is True
    assert res.provenance == DataProvenance.CALCULATED
    assert "estimated_road_distance_km" in res.data
    assert res.data["estimated_road_distance_km"] > 250

    route_tool = default_tool_registry.get("calculate_route")
    route_res = await route_tool.execute(stops=["Delhi", "Jaipur", "Udaipur"])
    assert route_res.success is True
    assert len(route_res.data["legs"]) == 2
    assert route_res.data["total_estimated_km"] > 500


@pytest.mark.asyncio
async def test_weather_tool_seasonal_advice():
    """Verify get_weather tool provides seasonal travel guidance and packing tips."""
    weather_tool = default_tool_registry.get("get_weather")
    assert weather_tool is not None

    res = await weather_tool.execute(destination="Himachal")
    assert res.success is True
    assert "temperature_range_celsius" in res.data
    assert "packing_recommendations" in res.data
    assert res.provenance == DataProvenance.ESTIMATE_RECOMMENDATION


@pytest.mark.asyncio
async def test_booking_tools_anti_hallucination_warning():
    """Verify booking tools clearly attach provenance and warnings when live suppliers are not verified."""
    hotel_tool = default_tool_registry.get("search_hotels")
    hotel_res = await hotel_tool.execute(city="Jaipur")
    assert hotel_res.success is True
    if not hotel_res.is_live_data:
        assert hotel_res.warning is not None
        assert "unavailable" in hotel_res.warning.lower() or "estimate" in hotel_res.warning.lower()

    flight_tool = default_tool_registry.get("search_flights")
    flight_res = await flight_tool.execute(origin="Kolkata", destination="Delhi")
    assert flight_res.success is True
    if not flight_res.is_live_data:
        assert flight_res.warning is not None
        assert "estimate" in flight_res.warning.lower() or "offline" in flight_res.warning.lower()


@pytest.mark.asyncio
async def test_itinerary_creation_and_trip_persistence():
    """Verify create_itinerary builds plan and save_trip / retrieve_trip can persist and reload."""
    create_tool = default_tool_registry.get("create_itinerary")
    save_tool = default_tool_registry.get("save_trip")
    retrieve_tool = default_tool_registry.get("retrieve_trip")

    # 1. Create itinerary
    itin_res = await create_tool.execute(destination="Rajasthan", days=5, travel_style="heritage")
    assert itin_res.success is True
    assert itin_res.data["duration_days"] == 5
    assert len(itin_res.data["days"]) == 5

    # 2. Save trip
    save_res = await save_tool.execute(
        title="5-Day Rajasthan Heritage",
        summary="A slow journey across Rajasthan forts and craft hubs.",
        total_budget="₹22,000 / person",
        days=itin_res.data["days"],
    )
    assert save_res.success is True
    trip_id = save_res.data["id"]
    share_token = save_res.data["share_token"]
    assert trip_id is not None

    # 3. Retrieve trip by share token
    load_res = await retrieve_tool.execute(trip_identifier=share_token)
    assert load_res.success is True
    assert load_res.data["title"] == "5-Day Rajasthan Heritage"
    assert len(load_res.data["days"]) == 5


@pytest.mark.asyncio
async def test_travel_agent_end_to_end_execution():
    """Verify TravelAgent runs the entire pipeline and returns structured AgentResponse."""
    agent = TravelAgent()

    # User query
    query = "Plan a 5-day Rajasthan trip."
    response = await agent.run(user_message=query)

    assert response.content
    assert response.intent == UserIntent.ITINERARY_PLANNING.value
    assert len(response.tools_used) > 0
    assert "search_destinations" in response.tools_used
    assert "create_itinerary" in response.tools_used
    assert response.duration_ms > 0
    assert isinstance(response.tool_results, list)
