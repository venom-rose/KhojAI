import { apiClient } from "./apiClient";
import { User } from "./auth";

export interface TravelPreferences {
  budget?: string;
  days?: string;
  style?: string;
  interests?: string[];
  group?: string;
  ai_pace?: string;
  ai_curiosity_level?: string;
}

export interface UserProfile extends User {
  travelPreferences: TravelPreferences;
  stats: {
    savedItinerariesCount: number;
    contributionsCount: number;
  };
}

export const userService = {
  async getProfile(): Promise<UserProfile> {
    const response = await apiClient.get("/users/me");
    const d = response.data;
    return {
      id: d.id,
      email: d.email,
      fullName: d.full_name,
      role: d.role,
      isActive: d.is_active,
      avatarUrl: d.avatar_url,
      bio: d.bio,
      themePreference: d.theme_preference,
      travelPreferences: d.travel_preferences || {},
      stats: {
        savedItinerariesCount: d.stats?.saved_itineraries_count || 0,
        contributionsCount: d.stats?.contributions_count || 0,
      },
      createdAt: d.created_at,
    };
  },

  async updateProfile(data: {
    fullName?: string;
    avatarUrl?: string;
    bio?: string;
    themePreference?: "light" | "dark" | "system";
  }): Promise<UserProfile> {
    const response = await apiClient.patch("/users/me", {
      full_name: data.fullName,
      avatar_url: data.avatarUrl,
      bio: data.bio,
      theme_preference: data.themePreference,
    });
    const d = response.data;
    return {
      id: d.id,
      email: d.email,
      fullName: d.full_name,
      role: d.role,
      isActive: d.is_active,
      avatarUrl: d.avatar_url,
      bio: d.bio,
      themePreference: d.theme_preference,
      travelPreferences: d.travel_preferences || {},
      stats: {
        savedItinerariesCount: d.stats?.saved_itineraries_count || 0,
        contributionsCount: d.stats?.contributions_count || 0,
      },
      createdAt: d.created_at,
    };
  },

  async updatePreferences(preferences: TravelPreferences): Promise<TravelPreferences> {
    const response = await apiClient.patch("/users/me/preferences", preferences);
    return response.data;
  },

  async deleteAccount(confirmation: string = "DELETE MY ACCOUNT"): Promise<void> {
    await apiClient.delete("/users/me", {
      data: { confirmation },
    });
  },
};
