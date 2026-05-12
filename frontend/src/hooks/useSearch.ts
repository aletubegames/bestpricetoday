import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import type { SearchResponse } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function useSearch(query: string) {
  return useQuery<SearchResponse>({
    queryKey: ["search", query],
    queryFn: async () => {
      const { data } = await axios.get(`${API_URL}/api/v1/search`, {
        params: { q: query, limit: 20 },
      });
      return data;
    },
    enabled: query.length >= 3,
    staleTime: 5 * 60 * 1000,
  });
}
