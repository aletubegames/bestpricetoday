import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import type { SearchResponse } from "@/types";
import { logger } from "@/lib/logger";
import { API_BASE as API_URL } from "@/lib/api";

export function useSearch(query: string) {
  return useQuery<SearchResponse>({
    queryKey: ["search", query],
    queryFn: async () => {
      try {
        const { data } = await axios.get(`${API_URL}/api/v1/search`, {
          params: { q: query, limit: 20 },
        });
        return data;
      } catch (error: unknown) {
        logger.error("Search failed:", axios.isAxiosError(error) ? error.message : error);
        throw new Error("Search failed");
      }
    },
    retry: 1,
    enabled: query.length >= 3,
    staleTime: 5 * 60 * 1000,
  });
}
