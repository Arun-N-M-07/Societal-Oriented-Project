export interface ScrapeResult {
  source_url: string;
  source_text: string;
}

export interface ScrapeResponse {
  source_url: string;
  source_text: string;
}

const API_BASE_URL = "http://127.0.0.1:8000";

export async function scrapeUrl(
  url: string
): Promise<ScrapeResponse> {
  const response = await fetch(`${API_BASE_URL}/api/admin/scrape`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      url,
    }),
  });

  let data: any = {};

  try {
    data = await response.json();
  } catch {
    throw new Error("Server returned an invalid response.");
  }

  if (!response.ok) {
    throw new Error(
      data.detail || "Unable to scrape the government website."
    );
  }

  return data;
}
