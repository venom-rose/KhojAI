export type TrustMetrics = {
  sourceQuality: number;
  recency: number;
  communityAgreement: number;
  completeness: number;
};

export type Destination = {
  slug: string;
  name: string;
  state: string;
  region: string;
  category: string;
  tags: string[];
  bestSeason: string;
  budget: string;
  trustScore: number;
  description: string;
  image: string;
  accent: string;
  coordinates: { x: string; y: string };
  trustMetrics: TrustMetrics;
  demoNote: string;
};

export const destinations: Destination[] = [
  {
    slug: "ziro",
    name: "Ziro",
    state: "Arunachal Pradesh",
    region: "Northeast",
    category: "Nature · Culture",
    tags: ["Slow travel", "Rice terraces", "Local food"],
    bestSeason: "Oct – Nov",
    budget: "₹₹",
    trustScore: 92,
    description: "A valley of emerald terraces, warm community stays and music that travels further than the road in.",
    image: "/images/ziro-valley.jpg",
    accent: "#5d6b43",
    coordinates: { x: "71%", y: "24%" },
    trustMetrics: { sourceQuality: 94, recency: 89, communityAgreement: 93, completeness: 91 },
    demoNote: "Illustrative demo content for MVP review; not a live travel advisory.",
  },
  {
    slug: "majuli",
    name: "Majuli",
    state: "Assam",
    region: "Northeast",
    category: "River · Culture",
    tags: ["Island life", "Satras", "Cycling"],
    bestSeason: "Nov – Feb",
    budget: "₹",
    trustScore: 88,
    description: "Move slowly through river-island life, where workshops, wetlands and long afternoons share the same horizon.",
    image: "/images/majuli-island.jpg",
    accent: "#b8734a",
    coordinates: { x: "67%", y: "30%" },
    trustMetrics: { sourceQuality: 88, recency: 86, communityAgreement: 90, completeness: 84 },
    demoNote: "Illustrative demo content for MVP review; not a live travel advisory.",
  },
  {
    slug: "tirthan-valley",
    name: "Tirthan Valley",
    state: "Himachal Pradesh",
    region: "Himalayas",
    category: "Forest · Outdoors",
    tags: ["River walks", "Cedar forest", "Cabin stays"],
    bestSeason: "Mar – Jun",
    budget: "₹₹",
    trustScore: 90,
    description: "A forest-fringed river corridor for long walks, clear water and the luxury of a quieter morning.",
    image: "/images/tirthan-valley.jpg",
    accent: "#34584d",
    coordinates: { x: "40%", y: "16%" },
    trustMetrics: { sourceQuality: 91, recency: 90, communityAgreement: 89, completeness: 90 },
    demoNote: "Illustrative demo content for MVP review; not a live travel advisory.",
  },
  {
    slug: "gandikota",
    name: "Gandikota",
    state: "Andhra Pradesh",
    region: "South",
    category: "Landscape · History",
    tags: ["Red gorge", "Sunrise", "Road trip"],
    bestSeason: "Oct – Feb",
    budget: "₹",
    trustScore: 84,
    description: "Terracotta cliffs, a river folded below and a horizon that makes the road feel like part of the destination.",
    image: "/images/gandikota-canyon.jpg",
    accent: "#b65c3d",
    coordinates: { x: "47%", y: "60%" },
    trustMetrics: { sourceQuality: 84, recency: 82, communityAgreement: 86, completeness: 83 },
    demoNote: "Illustrative demo content for MVP review; not a live travel advisory.",
  },
  {
    slug: "chopta",
    name: "Chopta",
    state: "Uttarakhand",
    region: "Himalayas",
    category: "Meadows · Trek",
    tags: ["Alpine trails", "Birding", "Sunrise"],
    bestSeason: "Apr – Jun",
    budget: "₹₹",
    trustScore: 87,
    description: "A small base for big skies, alpine walks and mountain mornings that begin before the rest of the valley.",
    image: "/images/chopta-meadows.jpg",
    accent: "#72885c",
    coordinates: { x: "42%", y: "22%" },
    trustMetrics: { sourceQuality: 87, recency: 85, communityAgreement: 88, completeness: 86 },
    demoNote: "Illustrative demo content for MVP review; not a live travel advisory.",
  },
  {
    slug: "orchha",
    name: "Orchha",
    state: "Madhya Pradesh",
    region: "Central India",
    category: "Heritage · Slow travel",
    tags: ["Riverside ruins", "Craft", "Architecture"],
    bestSeason: "Oct – Mar",
    budget: "₹",
    trustScore: 86,
    description: "A river, a ruined palace skyline and enough unhurried corners to make history feel close at hand.",
    image: "/images/orchha-palace.jpg",
    accent: "#a37c55",
    coordinates: { x: "39%", y: "43%" },
    trustMetrics: { sourceQuality: 86, recency: 88, communityAgreement: 84, completeness: 85 },
    demoNote: "Illustrative demo content for MVP review; not a live travel advisory.",
  },
  {
    slug: "dzukou-valley",
    name: "Dzukou Valley",
    state: "Nagaland",
    region: "Northeast",
    category: "Trek · Wildflowers",
    tags: ["High valley", "Seasonal bloom", "Trekking"],
    bestSeason: "Jun – Sep",
    budget: "₹₹",
    trustScore: 89,
    description: "A high valley of soft ridgelines and seasonal colour, reached one patient step at a time.",
    image: "/images/dzukou-valley.jpg",
    accent: "#9b6d3d",
    coordinates: { x: "72%", y: "34%" },
    trustMetrics: { sourceQuality: 90, recency: 87, communityAgreement: 91, completeness: 87 },
    demoNote: "Illustrative demo content for MVP review; not a live travel advisory.",
  },
  {
    slug: "gurez-valley",
    name: "Gurez Valley",
    state: "Jammu & Kashmir",
    region: "Himalayas",
    category: "Mountains · Culture",
    tags: ["Wooden homes", "High valley", "Community stays"],
    bestSeason: "May – Sep",
    budget: "₹₹₹",
    trustScore: 83,
    description: "A high-altitude valley where wooden homes, sharp peaks and generous local stories set the pace.",
    image: "/images/gurez-valley.jpg",
    accent: "#48677b",
    coordinates: { x: "29%", y: "9%" },
    trustMetrics: { sourceQuality: 82, recency: 80, communityAgreement: 87, completeness: 81 },
    demoNote: "Illustrative demo content for MVP review; not a live travel advisory.",
  },
];

export const regionOptions = ["All regions", "Himalayas", "Northeast", "Rajasthan", "Coastal India", "Central India", "South"];
export const interestOptions = ["Nature", "Culture", "Food", "Outdoors", "Heritage", "Slow travel"];

export const getDestination = (slug: string) => destinations.find((destination) => destination.slug === slug) ?? destinations[0];

export const featuredDestinations = destinations.slice(0, 4);

export const demoItinerary = {
  title: "A slower side of the Northeast",
  subtitle: "Ziro → Majuli · 5 days · 2 travellers",
  summary: "A considered loop through rice terraces, river-island culture and generous local tables — with enough blank space to wander.",
  totalBudget: "₹15,000 / person",
  days: [
    { day: "01", place: "Ziro", title: "Arrive into the green", body: "Settle into a community stay, then walk the terrace edges as the valley turns gold.", accent: "#6a7a4a" },
    { day: "02", place: "Ziro", title: "Make room for the ordinary", body: "Spend a morning with local food traditions and an afternoon with no fixed destination.", accent: "#b47b52" },
    { day: "03", place: "Majuli", title: "Cross into island time", body: "Take the ferry west and let the river reset your sense of distance.", accent: "#476b70" },
    { day: "04", place: "Majuli", title: "Stories, satras, sunset", body: "Cycle between craft workshops and a slow sunset by the water.", accent: "#9b6946" },
    { day: "05", place: "Majuli", title: "Leave with a longer horizon", body: "A final morning walk, a local breakfast and an unhurried route back.", accent: "#64794d" },
  ],
};

export const communityStories = [
  { name: "Ananya R.", role: "Local guide · Ziro", quote: "The best part of Ziro is not a single viewpoint. It is the way the valley makes you slow down.", tag: "Local perspective", time: "2 days ago", initials: "AR" },
  { name: "Rohit M.", role: "Weekend explorer · Pune", quote: "Majuli felt like pressing pause. We planned less and noticed more.", tag: "Recent stay", time: "1 week ago", initials: "RM" },
  { name: "Sonal K.", role: "Food researcher · Delhi", quote: "The signal I trust most is when several different travellers notice the same generous detail.", tag: "Trust note", time: "2 weeks ago", initials: "SK" },
];

export const trustSignals = [
  { label: "Community insights", value: "126", copy: "first-hand notes" },
  { label: "Seasonality", value: "12 mo", copy: "patterns mapped" },
  { label: "Access signals", value: "08", copy: "route notes" },
  { label: "Cost signals", value: "₹₹", copy: "relative, not live" },
];

export type PlannerPreferences = { budget: string; days: string; style: string; interests: string[]; group: string };

export const defaultPreferences: PlannerPreferences = { budget: "₹15,000", days: "5 days", style: "Slow travel", interests: ["Nature", "Culture"], group: "2 people" };

export type PlannerRecommendation = {
  destination: Destination;
  matchScore: number;
  budgetFit: number;
  styleFit: number;
  experienceFit: number;
  seasonFit: number;
  reasons: string[];
};

const budgetLevel = (budget: string) => budget.includes("25") ? 3 : budget.includes("8") ? 1 : 2;

const destinationBudgetLevel = (budget: string) => budget.length;

const fitScore = (base: number, hits: number, boost = 8) => Math.min(98, base + hits * boost);

export const buildPlannerRecommendations = (preferences: PlannerPreferences): PlannerRecommendation[] => {
  const styleWords: Record<string, string[]> = {
    "Slow travel": ["slow", "river", "local", "community", "culture"],
    Outdoors: ["forest", "trek", "trail", "mountain", "valley", "river"],
    "Culture-led": ["culture", "craft", "heritage", "architecture", "local"],
    "Road trip": ["road", "sunrise", "gorge", "landscape"],
  };
  const interestWords: Record<string, string[]> = { Nature: ["nature", "forest", "valley", "river", "mountain", "meadows", "landscape"], Culture: ["culture", "local", "craft", "heritage", "architecture", "satra"], Food: ["food", "local"], Outdoors: ["outdoors", "trek", "trail", "birding", "cycling"], Heritage: ["heritage", "ruins", "architecture", "craft"], "Slow travel": ["slow", "river", "island", "community"] };
  const targetBudget = budgetLevel(preferences.budget);
  const durationLabel = preferences.days === "10+ days" ? "extended" : preferences.days.replace(" days", "-day").replace(" day", "-day");
  return destinations.map((destination) => {
    const searchable = `${destination.category} ${destination.tags.join(" ")} ${destination.description}`.toLowerCase();
    const styleHits = (styleWords[preferences.style] ?? []).filter((word) => searchable.includes(word)).length;
    const experienceHits = preferences.interests.flatMap((interest) => interestWords[interest] ?? []).filter((word, index, words) => words.indexOf(word) === index && searchable.includes(word)).length;
    const budgetFit = Math.max(76, 100 - Math.abs(targetBudget - destinationBudgetLevel(destination.budget)) * 10);
    const styleFit = fitScore(72, styleHits, 5);
    const experienceFit = fitScore(72, experienceHits, 3);
    const seasonFit = Math.min(97, destination.trustMetrics.recency + 5);
    const matchScore = Math.round(styleFit * 0.24 + experienceFit * 0.23 + budgetFit * 0.18 + seasonFit * 0.15 + destination.trustScore * 0.2);
    const reasons = [
      experienceHits > 0 ? `Fits your ${preferences.interests[0]?.toLowerCase() ?? "experience"} preference` : "Adds a different texture to your brief",
      styleFit >= 85 ? `Matches your ${preferences.style.toLowerCase()} style` : "Offers a flexible pace for your trip",
      budgetFit >= 90 ? "Within your selected budget" : "Keeps the budget signal visible",
      destination.trustScore >= 88 ? "Strong destination confidence" : "Useful context, with a little more to verify",
      `Good fit for your ${durationLabel} trip`,
    ];
    return { destination, matchScore, budgetFit, styleFit, experienceFit, seasonFit, reasons };
  }).sort((a, b) => b.matchScore - a.matchScore).slice(0, 3);
};
