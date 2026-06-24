import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import type { TrendingSearchResponse } from "@/types";

import { API_BASE as API_URL } from "@/lib/api";

export function useTrendingSearches(limit = 8) {
  return useQuery<TrendingSearchResponse>({
    queryKey: ["trending-searches", limit],
    queryFn: async () => {
      const { data } = await axios.get(`${API_URL}/api/v1/search/trending`, {
        params: { limit },
      });
      return data;
    },
    staleTime: 60 * 1000,
    refetchInterval: 60 * 1000,
  });
}