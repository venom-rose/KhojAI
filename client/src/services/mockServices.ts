import { defaultPreferences, destinations, Destination, demoItinerary, PlannerPreferences } from "@/data/destinations";

const wait = (ms = 180) => new Promise((resolve) => setTimeout(resolve, ms));

export const destinationService = {
  async getDestinations(): Promise<Destination[]> {
    await wait();
    return destinations;
  },
  async getDestinationBySlug(slug: string): Promise<Destination> {
    await wait(120);
    return destinations.find((destination) => destination.slug === slug) ?? destinations[0];
  },
};

export const recommendationService = {
  async getRecommendations(): Promise<Destination[]> {
    await wait();
    return destinations.slice(0, 4);
  },
};

export const plannerService = {
  async generateItinerary(preferences: PlannerPreferences = defaultPreferences) {
    await wait(750);
    return { ...demoItinerary, subtitle: `${preferences.style} · ${preferences.days} · ${preferences.group}` };
  },
};

export const contributionService = {
  async submitContribution(payload: { place: string; story: string; name: string }) {
    await wait(500);
    return { ok: true, message: `Thanks${payload.name ? `, ${payload.name}` : ""}. Your note is saved as a demo contribution.` };
  },
};
