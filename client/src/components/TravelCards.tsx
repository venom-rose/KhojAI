import React, { useState } from "react";
import {
  StructuredCard,
  DestinationCardData,
  HotelCardData,
  ActivityCardData,
  FlightCardData,
  ItineraryCardData,
  MapCardData,
  ErrorCardData,
} from "@/services/chat";
import {
  AlertCircle,
  Calendar,
  ChevronDown,
  ChevronRight,
  Clock,
  ExternalLink,
  Info,
  MapPin,
  Plane,
  ShieldCheck,
  Sparkles,
  Star,
  Users,
  Wallet,
} from "lucide-react";
import { Link } from "wouter";

export function TravelCardRenderer({ card }: { card: StructuredCard }) {
  switch (card.type) {
    case "destination":
      return <DestinationCardView data={card.data as DestinationCardData} />;
    case "hotel":
      return <HotelCardView data={card.data as HotelCardData} />;
    case "activity":
      return <ActivityCardView data={card.data as ActivityCardData} />;
    case "flight":
      return <FlightCardView data={card.data as FlightCardData} />;
    case "itinerary":
      return <ItineraryTimelineView data={card.data as ItineraryCardData} />;
    case "map":
      return <MapCardView data={card.data as MapCardData} />;
    case "error":
      return <ErrorCardView data={card.data as ErrorCardData} />;
    default:
      return null;
  }
}

// 1. Destination Card
function DestinationCardView({ data }: { data: DestinationCardData }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-white shadow-sm transition hover:shadow-md">
      <div className="relative h-28 w-full bg-mist overflow-hidden">
        <img
          src={data.image || "/images/hero-himalayas.jpg"}
          alt={data.name}
          className="h-full w-full object-cover"
          onError={(e) => {
            const target = e.currentTarget as HTMLImageElement;
            if (!target.src.includes("hero-himalayas.jpg")) {
              target.src = "/images/hero-himalayas.jpg";
            }
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent" />
        <div className="absolute bottom-2 left-3 right-3 flex items-end justify-between text-white">
          <div>
            <p className="font-mono text-[9px] uppercase tracking-wider text-saffron-light">
              {data.state} · {data.region}
            </p>
            <h4 className="font-display text-lg font-semibold tracking-tight">
              {data.name}
            </h4>
          </div>
          <span className="flex items-center gap-1 rounded-full bg-olive px-2 py-0.5 font-mono text-[10px] font-bold text-white shadow">
            <ShieldCheck size={11} />
            {data.trust_score}%
          </span>
        </div>
      </div>
      <div className="p-3">
        <p className="line-clamp-2 text-xs leading-relaxed text-ink/70">
          {data.description || "Curated offbeat destination with verified seasonal timings."}
        </p>
        {data.explanation && (
          <div className="mt-2 flex items-start gap-1.5 rounded-lg bg-olive/10 p-2 text-[11px] text-olive">
            <Sparkles size={13} className="shrink-0 mt-0.5 text-olive" />
            <span>{data.explanation}</span>
          </div>
        )}
        <div className="mt-3 flex items-center justify-between border-t border-line/60 pt-2 text-[10px] text-ink/50 font-medium">
          <span>Best season: {data.best_season}</span>
          <Link
            href={`/destination/${data.id}`}
            className="inline-flex items-center gap-1 font-semibold text-saffron hover:underline"
          >
            Explore Guide <ChevronRight size={11} />
          </Link>
        </div>
      </div>
    </div>
  );
}

// 2. Hotel Card
function HotelCardView({ data }: { data: HotelCardData }) {
  return (
    <div className="rounded-2xl border border-line bg-white p-3.5 shadow-sm transition hover:shadow-md">
      <div className="flex items-start justify-between gap-2">
        <div>
          <span className="inline-block rounded-full bg-mist px-2 py-0.5 font-mono text-[9px] uppercase tracking-wider text-ink/60">
            {data.stay_type || "Homestay"}
          </span>
          <h4 className="mt-1 font-display text-base font-semibold text-ink">
            {data.name}
          </h4>
          {data.city && (
            <p className="flex items-center gap-1 text-[11px] text-ink/50">
              <MapPin size={11} className="text-saffron" /> {data.city}
            </p>
          )}
        </div>
        <div className="text-right">
          <p className="font-display text-base font-bold text-ink">
            ₹{data.price_per_night_inr.toLocaleString()}
          </p>
          <p className="font-mono text-[9px] text-ink/40">per night</p>
        </div>
      </div>

      {data.explanation && (
        <div className="mt-2.5 rounded-lg bg-olive/10 p-2 text-[11px] text-olive flex items-start gap-1.5">
          <Sparkles size={12} className="shrink-0 mt-0.5" />
          <span>{data.explanation}</span>
        </div>
      )}

      {data.amenities && data.amenities.length > 0 && (
        <div className="mt-2.5 flex flex-wrap gap-1">
          {data.amenities.slice(0, 3).map((amenity, i) => (
            <span
              key={i}
              className="rounded-md bg-mist px-1.5 py-0.5 text-[10px] text-ink/65"
            >
              {amenity}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// 3. Activity / Attraction Card
function ActivityCardView({ data }: { data: ActivityCardData }) {
  return (
    <div className="rounded-2xl border border-line bg-white p-3.5 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <div>
          <span className="rounded-full bg-saffron/10 px-2 py-0.5 font-mono text-[9px] uppercase tracking-wider text-saffron">
            {data.category || (data.is_attraction ? "Attraction" : "Activity")}
          </span>
          <h4 className="mt-1 font-display text-sm font-semibold text-ink">
            {data.title}
          </h4>
        </div>
        <div className="flex items-center gap-1 font-mono text-[11px] font-semibold text-ink">
          {data.price_inr && data.price_inr > 0 ? `₹${data.price_inr}` : "Free"}
        </div>
      </div>
      {data.description && (
        <p className="mt-1.5 text-xs text-ink/65 line-clamp-2">{data.description}</p>
      )}
      {data.explanation && (
        <p className="mt-2 text-[11px] text-olive font-medium flex items-center gap-1">
          <Sparkles size={11} /> {data.explanation}
        </p>
      )}
      <div className="mt-2.5 flex items-center gap-3 border-t border-line/60 pt-2 text-[10px] text-ink/50">
        {data.duration_hours && (
          <span className="flex items-center gap-1">
            <Clock size={10} /> {data.duration_hours}h duration
          </span>
        )}
        {data.recommended_timing && (
          <span className="flex items-center gap-1">
            <Calendar size={10} /> {data.recommended_timing}
          </span>
        )}
      </div>
    </div>
  );
}

// 4. Flight Result Card
function FlightCardView({ data }: { data: FlightCardData }) {
  return (
    <div className="rounded-2xl border border-line bg-white p-3.5 shadow-sm">
      <div className="flex items-center justify-between border-b border-line/60 pb-2">
        <span className="flex items-center gap-1.5 font-semibold text-xs text-ink">
          <Plane size={13} className="text-saffron" />
          {data.airline}
        </span>
        <span className="font-display text-sm font-bold text-ink">
          ₹{data.price_inr.toLocaleString()}
        </span>
      </div>
      <div className="mt-2.5 flex items-center justify-between text-center">
        <div className="text-left">
          <p className="font-display text-base font-bold text-ink">{data.departure_time}</p>
          <p className="font-mono text-[10px] text-ink/50 uppercase">{data.origin}</p>
        </div>
        <div className="px-3">
          <p className="font-mono text-[9px] text-ink/40">{data.duration}</p>
          <div className="relative my-1 flex items-center">
            <div className="h-px w-16 bg-line" />
            <span className="size-1.5 rounded-full bg-saffron" />
          </div>
          <p className="font-mono text-[9px] text-olive">
            {data.stops === 0 ? "Non-stop" : `${data.stops} stop`}
          </p>
        </div>
        <div className="text-right">
          <p className="font-display text-base font-bold text-ink">{data.arrival_time}</p>
          <p className="font-mono text-[10px] text-ink/50 uppercase">{data.destination}</p>
        </div>
      </div>
      {data.is_estimate && (
        <p className="mt-2 text-[9px] text-ink/40 italic">
          * Indicative schedule & fare estimate based on route benchmarks.
        </p>
      )}
    </div>
  );
}

// 5. Itinerary Timeline Card
function ItineraryTimelineView({ data }: { data: ItineraryCardData }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-2xl border border-line bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3 border-b border-line/60 pb-3">
        <div>
          <span className="rounded-full bg-olive/15 px-2 py-0.5 font-mono text-[9px] uppercase tracking-wider text-olive font-semibold">
            {data.duration_days} Days · {data.pacing_rating}
          </span>
          <h4 className="mt-1 font-display text-base font-semibold text-ink">
            {data.destination} Itinerary
          </h4>
        </div>
        {data.estimated_cost?.total_estimated_inr && (
          <div className="text-right">
            <p className="font-display text-base font-bold text-ink">
              ₹{data.estimated_cost.total_estimated_inr.toLocaleString()}
            </p>
            <p className="font-mono text-[9px] text-ink/40">Est. Total</p>
          </div>
        )}
      </div>

      {data.summary && (
        <p className="mt-2.5 text-xs text-ink/70 leading-relaxed">{data.summary}</p>
      )}

      {/* Days Preview */}
      <div className="mt-3 space-y-2">
        {data.days.slice(0, expanded ? data.days.length : 2).map((day) => (
          <div key={day.day_number} className="rounded-xl bg-mist/60 p-2.5 text-xs">
            <div className="flex items-center justify-between font-semibold text-ink">
              <span>Day {day.day_number}: {day.title}</span>
              {day.neighborhood_cluster && (
                <span className="font-mono text-[9px] text-ink/50">
                  {day.neighborhood_cluster}
                </span>
              )}
            </div>
            {day.morning?.theme && (
              <p className="mt-1 text-[11px] text-ink/60">
                <strong className="text-ink/75">Morning:</strong> {day.morning.theme}
              </p>
            )}
            {day.afternoon?.theme && (
              <p className="mt-0.5 text-[11px] text-ink/60">
                <strong className="text-ink/75">Afternoon:</strong> {day.afternoon.theme}
              </p>
            )}
          </div>
        ))}
      </div>

      {data.days.length > 2 && (
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="mt-3 inline-flex items-center gap-1 font-mono text-[11px] font-semibold text-saffron hover:underline"
        >
          {expanded ? "Show less" : `View all ${data.days.length} days`}
          <ChevronDown size={12} className={`transition ${expanded ? "rotate-180" : ""}`} />
        </button>
      )}
    </div>
  );
}

// 6. Map / Location Card
function MapCardView({ data }: { data: MapCardData }) {
  const mapUrl = `https://www.google.com/maps/search/?api=1&query=${data.latitude},${data.longitude}`;

  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-paper p-3 text-xs shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="grid size-7 place-items-center rounded-full bg-saffron/10 text-saffron">
            <MapPin size={14} />
          </span>
          <div>
            <h4 className="font-semibold text-ink">{data.title}</h4>
            <p className="font-mono text-[10px] text-ink/50">
              {data.latitude.toFixed(4)}°N, {data.longitude.toFixed(4)}°E
            </p>
          </div>
        </div>
        <a
          href={mapUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 rounded-full border border-line bg-white px-2.5 py-1 text-[11px] font-medium text-ink hover:border-ink transition"
        >
          View Map <ExternalLink size={11} />
        </a>
      </div>
      {data.description && (
        <p className="mt-2 text-[11px] text-ink/60">{data.description}</p>
      )}
    </div>
  );
}

// 7. Error Card
function ErrorCardView({ data }: { data: ErrorCardData }) {
  return (
    <div className="flex items-start gap-2.5 rounded-xl border border-amber-200 bg-amber-50/60 p-3 text-xs text-amber-900">
      <AlertCircle size={15} className="mt-0.5 shrink-0 text-amber-600" />
      <div>
        <p className="font-semibold">{data.message}</p>
        {data.warning && <p className="mt-0.5 text-[11px] text-amber-700">{data.warning}</p>}
      </div>
    </div>
  );
}
