"""Curated, verified seed data for Indian offbeat travel intelligence in KHOJAI."""

SEED_DATA = {
    "countries": [
        {
            "code": "IN",
            "name": "India",
            "currency": "INR",
            "phone_code": "+91",
            "continent": "Asia",
            "source": "seed_verified",
            "source_id": "ISO-3166-IN",
        }
    ],
    "states": [
        {
            "country_code": "IN",
            "name": "Arunachal Pradesh",
            "code": "AR",
            "region": "Northeast",
            "source": "seed_verified",
            "source_id": "ISO-3166-2:IN-AR",
        },
        {
            "country_code": "IN",
            "name": "Assam",
            "code": "AS",
            "region": "Northeast",
            "source": "seed_verified",
            "source_id": "ISO-3166-2:IN-AS",
        },
        {
            "country_code": "IN",
            "name": "Himachal Pradesh",
            "code": "HP",
            "region": "Himalayas",
            "source": "seed_verified",
            "source_id": "ISO-3166-2:IN-HP",
        },
    ],
    "cities": [
        {
            "state_name": "Arunachal Pradesh",
            "name": "Naharlagun",
            "city_code": "NHLN",
            "latitude": 27.1064,
            "longitude": 93.6934,
            "elevation_meters": 290,
            "source": "seed_verified",
            "source_id": "geo/nhln",
        },
        {
            "state_name": "Assam",
            "name": "Jorhat",
            "city_code": "JRH",
            "latitude": 26.7509,
            "longitude": 94.2037,
            "elevation_meters": 116,
            "source": "seed_verified",
            "source_id": "geo/jrh",
        },
        {
            "state_name": "Himachal Pradesh",
            "name": "Kullu",
            "city_code": "KLU",
            "latitude": 31.9579,
            "longitude": 77.1095,
            "elevation_meters": 1278,
            "source": "seed_verified",
            "source_id": "geo/klu",
        },
    ],
    "categories": [
        {
            "slug": "living-heritage-cultural-landscape",
            "name": "Living Heritage & Cultural Landscape",
            "description": "Indigenous agrarian communities, UNESCO tentative cultural landscapes, and living architecture.",
            "icon_name": "Landmark",
            "source": "seed_verified",
            "source_id": "cat/cultural-landscape",
        },
        {
            "slug": "riverine-island-ecosystem",
            "name": "Riverine Island & Wetland Sanctuary",
            "description": "Dynamic braided river habitats, monastic satras, and endangered migratory flyways.",
            "icon_name": "Waves",
            "source": "seed_verified",
            "source_id": "cat/riverine-island",
        },
        {
            "slug": "high-altitude-alpine-valley",
            "name": "High-Altitude Alpine Valley",
            "description": "Pristine glacial valleys, sub-Himalayan cedar forests, and remote mountain hamlets.",
            "icon_name": "MountainSnow",
            "source": "seed_verified",
            "source_id": "cat/alpine-valley",
        },
    ],
    "airports": [
        {
            "city_name": "Naharlagun",
            "name": "Donyi Polo Airport, Hollongi",
            "iata_code": "HGI",
            "icao_code": "VEHO",
            "latitude": 26.9697,
            "longitude": 93.6394,
            "is_international": False,
            "source": "seed_verified",
            "source_id": "airport/hgi",
        },
        {
            "city_name": "Jorhat",
            "name": "Jorhat Airport (Rowriah)",
            "iata_code": "JRH",
            "icao_code": "VEJT",
            "latitude": 26.7317,
            "longitude": 94.1754,
            "is_international": False,
            "source": "seed_verified",
            "source_id": "airport/jrh",
        },
        {
            "city_name": "Kullu",
            "name": "Kullu-Manali Airport, Bhuntar",
            "iata_code": "KUU",
            "icao_code": "VIBR",
            "latitude": 31.8767,
            "longitude": 77.1544,
            "is_international": False,
            "source": "seed_verified",
            "source_id": "airport/kuu",
        },
    ],
    "destinations": [
        {
            "slug": "ziro",
            "name": "Ziro Valley",
            "state": "Arunachal Pradesh",
            "region": "Northeast",
            "category": "Living Heritage & Cultural Landscape",
            "category_slug": "living-heritage-cultural-landscape",
            "city_name": "Naharlagun",
            "best_season": "Sep – Nov",
            "budget": "₹₹",
            "trust_score": 94,
            "description": (
                "Perched at 1,500 meters in lower Subansiri, Ziro Valley is the ancestral cradle of the Apatani tribe. "
                "The valley is renowned for its UNESCO-nominated sustainable agriculture system combining paddy cultivation "
                "with fish farming, surrounded by bamboo groves and pine-clad hills. Village settlements like Hong and Hari "
                "preserve deep animist Donyi-Polo traditions, sacred lapangs, and unhurried hospitality."
            ),
            "image_url": "https://images.unsplash.com/photo-1596401057633-54a8fe8ef647?auto=format&fit=crop&w=1400&q=80",
            "latitude": 27.5950,
            "longitude": 93.8385,
            "is_hidden_gem": True,
            "accent_color": "#4a5d3f",
            "coordinate_x": "78%",
            "coordinate_y": "28%",
            "demo_note": "Travelers must procure an Inner Line Permit (ILP) or Protected Area Permit (PAP) before entering Arunachal Pradesh.",
            "source": "seed_verified",
            "source_id": "dest/ziro",
            "tags": ["Apatani Culture", "Paddy Fish Farming", "Pine Ridges", "Donyi Polo"],
            "seasons": [
                {
                    "season_name": "Autumn Harvest",
                    "start_month": 9,
                    "end_month": 11,
                    "weather_summary": "Crisp sunny days with golden rice fields and cool mountain breezes.",
                    "avg_temp_min_c": 8.0,
                    "avg_temp_max_c": 22.0,
                    "rainfall_level": "low",
                    "is_recommended": True,
                    "advisory_notes": "Ideal for village walks and music fest season; book homestays months ahead.",
                },
                {
                    "season_name": "Spring Bloom",
                    "start_month": 3,
                    "end_month": 5,
                    "weather_summary": "Rhododendrons and wild orchids in bloom with mild afternoon rains.",
                    "avg_temp_min_c": 12.0,
                    "avg_temp_max_c": 24.0,
                    "rainfall_level": "moderate",
                    "is_recommended": True,
                    "advisory_notes": "Pleasant climate, Myoko festival observed in late March.",
                },
            ],
            "tips": [
                {
                    "category": "logistics",
                    "title": "Procure Arunachal ILP in Advance",
                    "content": "Indian citizens require an online Inner Line Permit (ILP) via arunachalilp.gov.in. Foreign nationals require a Protected Area Permit (PAP).",
                    "priority": 1,
                },
                {
                    "category": "etiquette",
                    "title": "Respect Clan Lapangs and Sacred Groves",
                    "content": "Village lapangs (wooden community platforms) are sacred gathering spaces. Always seek permission before sitting or photographing ceremonies.",
                    "priority": 2,
                },
            ],
            "attractions": [
                {
                    "name": "Hong Village & Sacred Lapang",
                    "category": "Heritage Site",
                    "description": "One of the largest traditional Apatani villages featuring stilt bamboo homes, totems, and community platforms.",
                    "latitude": 27.5750,
                    "longitude": 93.8500,
                    "entry_fee": "Free",
                    "timings": "Daylight hours",
                    "difficulty": "Easy",
                    "recommended_duration_mins": 150,
                    "tags": ["Heritage", "Community", "Architecture"],
                },
                {
                    "name": "Tarin High-Altitude Fish Farm",
                    "category": "Ecological Landmark",
                    "description": "Traditional aquaculture site surrounded by bamboo and blue pine groves demonstrating organic paddy-fish symbiosis.",
                    "latitude": 27.6010,
                    "longitude": 93.8320,
                    "entry_fee": "₹20",
                    "timings": "09:00 AM – 05:00 PM",
                    "difficulty": "Easy",
                    "recommended_duration_mins": 60,
                    "tags": ["Ecology", "Farming", "Nature"],
                },
            ],
            "activities": [
                {
                    "title": "Apatani Village & Paddy Walk",
                    "activity_type": "Guided Cultural Walk",
                    "description": "Led by local youth through village alleyways, community granaries, and canal systems.",
                    "duration_hours": 3.0,
                    "price_range": "₹800 per group",
                    "seasonality": "All year",
                    "guide_required": True,
                }
            ],
            "hotels": [
                {
                    "name": "Donyi Hango Apatani Homestay",
                    "stay_type": "Homestay",
                    "address": "Hong Village, Ziro",
                    "latitude": 27.5760,
                    "longitude": 93.8510,
                    "price_per_night": "₹1,800 – ₹2,500",
                    "price_level": "₹₹",
                    "rating": 4.8,
                    "amenities": ["Wood-fire hearth", "Traditional meals", "Local guide assistance"],
                    "sustainability_rating": 95,
                }
            ],
            "restaurants": [
                {
                    "name": "Apatani Hearth Kitchen",
                    "cuisine_type": "Indigenous Tribal",
                    "address": "Old Ziro Market Road",
                    "latitude": 27.5920,
                    "longitude": 93.8350,
                    "price_range": "₹",
                    "rating": 4.6,
                    "must_try_dishes": ["Piku bamboo shoot mash", "Steamed red hill rice", "Boiled garden greens"],
                    "opening_hours": "11:30 AM – 08:30 PM",
                }
            ],
            "transportation_options": [
                {
                    "transport_type": "Shared Sumo Taxi",
                    "origin_name": "Naharlagun Railway Station",
                    "destination_name": "Hapoli / Ziro Town",
                    "duration_hours": 3.5,
                    "cost_estimate": "₹350 per seat",
                    "frequency": "Hourly between 06:00 AM and 11:00 AM",
                    "operator_name": "Subansiri Shared Sumo Syndicate",
                    "booking_tips": "Arrive at station exit counter early morning; seats fill rapidly.",
                }
            ],
            "travel_routes": [
                {
                    "route_name": "Naharlagun to Ziro via Potin",
                    "mode": "Road",
                    "distance_km": 98.0,
                    "typical_duration_hours": 3.5,
                    "road_condition": "Two-lane mountain road with smooth paved asphalt and scenic river gorges.",
                    "scenic_rating": 9,
                    "seasonal_notes": "Occasional monsoon mud deposits in July; clear during Autumn.",
                }
            ],
        },
        {
            "slug": "majuli",
            "name": "Majuli Island",
            "state": "Assam",
            "region": "Northeast",
            "category": "Riverine Island & Wetland Sanctuary",
            "category_slug": "riverine-island-ecosystem",
            "city_name": "Jorhat",
            "best_season": "Oct – Mar",
            "budget": "₹",
            "trust_score": 92,
            "description": (
                "The world's largest populated river island resting in the heart of the mighty Brahmaputra, Majuli is the "
                "epicenter of Assam's Neo-Vaishnavite culture. Home to centuries-old Satras (monastic institutions), traditional "
                "bamboo mask making, and the indigenous Mishing river community living on wooden chang-ghars."
            ),
            "image_url": "https://images.unsplash.com/photo-1544735716-392fe2489ffa?auto=format&fit=crop&w=1400&q=80",
            "latitude": 26.9535,
            "longitude": 94.2045,
            "is_hidden_gem": True,
            "accent_color": "#2d6a7f",
            "coordinate_x": "82%",
            "coordinate_y": "34%",
            "demo_note": "Ferry crossings from Jorhat (Nimati Ghat) are suspended during severe Brahmaputra flooding.",
            "source": "seed_verified",
            "source_id": "dest/majuli",
            "tags": ["River Island", "Satra Culture", "Mask Making", "Mishing Tribe"],
            "seasons": [
                {
                    "season_name": "Winter Migratory Season",
                    "start_month": 11,
                    "end_month": 2,
                    "weather_summary": "Pleasant morning fog, warm afternoons, and flocks of Siberian cranes in wetlands.",
                    "avg_temp_min_c": 10.0,
                    "avg_temp_max_c": 24.0,
                    "rainfall_level": "dry",
                    "is_recommended": True,
                    "advisory_notes": "Best time for cycling across island dikes and birdwatching.",
                }
            ],
            "tips": [
                {
                    "category": "logistics",
                    "title": "Check Ferry Schedules at Nimati Ghat",
                    "content": "Government Ro-Pax and wooden ferries run from Nimati Ghat (Jorhat) to Kamalabari Ghat every 60-90 minutes from 7 AM to 4 PM.",
                    "priority": 1,
                }
            ],
            "attractions": [
                {
                    "name": "Samaguri Satra (Traditional Mask Center)",
                    "category": "Cultural Heritage",
                    "description": "Historic monastic center preserving traditional cane, bamboo, and mud mask making for Bhaona performances.",
                    "latitude": 26.9600,
                    "longitude": 94.2400,
                    "entry_fee": "Free (donations welcome)",
                    "timings": "09:00 AM – 05:00 PM",
                    "difficulty": "Easy",
                    "recommended_duration_mins": 90,
                    "tags": ["Culture", "Craft", "Masks"],
                }
            ],
            "activities": [
                {
                    "title": "Majuli Traditional Mask-Making Workshop",
                    "activity_type": "Cultural Workshop",
                    "description": "Learn bamboo frame structuring and organic clay molding with master artisans.",
                    "duration_hours": 2.5,
                    "price_range": "₹500 per person",
                    "seasonality": "Oct – May",
                    "guide_required": True,
                }
            ],
            "hotels": [
                {
                    "name": "La Maison de Ananda",
                    "stay_type": "Eco-Lodge",
                    "address": "Karbong, Garamur, Majuli",
                    "latitude": 26.9630,
                    "longitude": 94.2080,
                    "price_per_night": "₹1,200 – ₹2,000",
                    "price_level": "₹",
                    "rating": 4.7,
                    "amenities": ["Traditional bamboo stilt rooms", "Mishing home meals", "Bicycle rentals"],
                    "sustainability_rating": 94,
                }
            ],
            "restaurants": [
                {
                    "name": "Ural Majuli Kitchen",
                    "cuisine_type": "Assamese Thali",
                    "address": "Near Kamalabari Tiniali, Majuli",
                    "latitude": 26.9480,
                    "longitude": 94.1980,
                    "price_range": "₹",
                    "rating": 4.5,
                    "must_try_dishes": ["Brahmaputra fish thali", "Dhekia saag", "Khar"],
                    "opening_hours": "11:00 AM – 08:00 PM",
                }
            ],
            "transportation_options": [
                {
                    "transport_type": "River Ferry",
                    "origin_name": "Jorhat Nimati Ghat",
                    "destination_name": "Kamalabari Ghat, Majuli",
                    "duration_hours": 1.0,
                    "cost_estimate": "₹15 per person / ₹700 car",
                    "frequency": "Hourly from 07:00 AM to 04:00 PM",
                    "operator_name": "Inland Water Transport Assam",
                    "booking_tips": "Ticket counters operate on-site; Ro-Pax vessel handles four-wheelers.",
                }
            ],
            "travel_routes": [
                {
                    "route_name": "Jorhat to Majuli via Nimati Ghat Ferry",
                    "mode": "Road + Ferry",
                    "distance_km": 28.0,
                    "typical_duration_hours": 1.5,
                    "road_condition": "Paved road to ghat, followed by river crossing on Brahmaputra.",
                    "scenic_rating": 9,
                    "seasonal_notes": "Winter river levels may require short sandbar walks.",
                }
            ],
        },
        {
            "slug": "tirthan-valley",
            "name": "Tirthan Valley",
            "state": "Himachal Pradesh",
            "region": "Himalayas",
            "category": "High-Altitude Alpine Valley",
            "category_slug": "high-altitude-alpine-valley",
            "city_name": "Kullu",
            "best_season": "Mar – Jun & Oct – Nov",
            "budget": "₹₹",
            "trust_score": 93,
            "description": (
                "Flanked by the Great Himalayan National Park (a UNESCO World Heritage Site), Tirthan Valley is an unhurried "
                "sanctuary of glacial rivers, dense deodar forests, and slate-roofed Kathkuni wooden cottages. Free from commercial "
                "crowds, it is a haven for angling, tranquil forest walks, and gateway treks."
            ),
            "image_url": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=1400&q=80",
            "latitude": 31.6420,
            "longitude": 77.3410,
            "is_hidden_gem": True,
            "accent_color": "#2c5d4f",
            "coordinate_x": "32%",
            "coordinate_y": "22%",
            "demo_note": "Single-use plastics are strictly regulated within the eco-zone buffer.",
            "source": "seed_verified",
            "source_id": "dest/tirthan-valley",
            "tags": ["Alpine Valley", "Trout Angling", "Kathkuni Architecture", "GHNP Gateway"],
            "seasons": [
                {
                    "season_name": "Spring & Summer",
                    "start_month": 3,
                    "end_month": 6,
                    "weather_summary": "Sunny mountain days, blooming apple orchards, and roaring river rapids.",
                    "avg_temp_min_c": 12.0,
                    "avg_temp_max_c": 26.0,
                    "rainfall_level": "moderate",
                    "is_recommended": True,
                    "advisory_notes": "Excellent weather for day hikes to waterfalls and forest trails.",
                }
            ],
            "tips": [
                {
                    "category": "logistics",
                    "title": "Turn Off at Aut Tunnel",
                    "content": "Take the diversion immediately before Aut tunnel on the Chandigarh-Manali highway towards Larji and Banjar.",
                    "priority": 1,
                }
            ],
            "attractions": [
                {
                    "name": "Chhoie Waterfall & Cedar Trail",
                    "category": "Waterfall & Forest",
                    "description": "Hidden waterfall reached by a scenic 45-minute trek through sacred deodar groves.",
                    "latitude": 31.6380,
                    "longitude": 77.3450,
                    "entry_fee": "Free",
                    "timings": "Sunrise to Sunset",
                    "difficulty": "Moderate",
                    "recommended_duration_mins": 90,
                    "tags": ["Trek", "Nature", "Waterfall"],
                }
            ],
            "activities": [
                {
                    "title": "Tirthan River Angling & Forest Trail",
                    "activity_type": "Eco Adventure",
                    "description": "Catch-and-release brown trout fishing permit with local angler companion.",
                    "duration_hours": 3.0,
                    "price_range": "₹1,200 per permit",
                    "seasonality": "Mar – Oct",
                    "guide_required": True,
                }
            ],
            "hotels": [
                {
                    "name": "Tirthan Pine Eco-Cottage",
                    "stay_type": "Eco-Lodge",
                    "address": "Gushaini Village, Tirthan Valley",
                    "latitude": 31.6450,
                    "longitude": 77.3440,
                    "price_per_night": "₹2,200 – ₹3,500",
                    "price_level": "₹₹",
                    "rating": 4.9,
                    "amenities": ["Riverside balcony", "Organic orchard produce", "Trek guide"],
                    "sustainability_rating": 96,
                }
            ],
            "restaurants": [
                {
                    "name": "Himalayan Trout Dhaba",
                    "cuisine_type": "Himachali / Trout Specialty",
                    "address": "Banjar Market Road, Tirthan",
                    "latitude": 31.6350,
                    "longitude": 77.3400,
                    "price_range": "₹₹",
                    "rating": 4.7,
                    "must_try_dishes": ["Pan-seared river trout with herbs", "Siddu with ghee", "Himachali Madra"],
                    "opening_hours": "12:00 PM – 09:00 PM",
                }
            ],
            "transportation_options": [
                {
                    "transport_type": "Private Cab / Shared Taxi",
                    "origin_name": "Aut Tunnel Bus Stop",
                    "destination_name": "Gushaini / Tirthan Valley",
                    "duration_hours": 1.2,
                    "cost_estimate": "₹1,000 cab / ₹60 local bus",
                    "frequency": "Frequent local buses until 05:00 PM",
                    "operator_name": "Banjar Valley Transport",
                    "booking_tips": "Buses from Delhi to Manali will drop you right before Aut Tunnel.",
                }
            ],
            "travel_routes": [
                {
                    "route_name": "Chandigarh to Tirthan Valley via Kiratpur & Mandi",
                    "mode": "Road",
                    "distance_km": 245.0,
                    "typical_duration_hours": 6.5,
                    "road_condition": "Four-lane highway up to Mandi, then scenic two-lane mountain highway.",
                    "scenic_rating": 9,
                    "seasonal_notes": "Pleasant drive; carry warm clothes for evening temperatures.",
                }
            ],
        },
    ],
}
