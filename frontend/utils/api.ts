// API utility helper for Car Speed Simulation
// Handles environment-based API base URL configuration

// API base URL with fallback for development
const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 
  (process.env.NODE_ENV === "development" ? "" : "");

/**
 * Creates a full API URL with proper base URL handling
 * @param path - API endpoint path (e.g., "/api/auto-route")
 * @returns Full API URL
 */
export const api = (path: string): string => {
  // Remove leading slash if present to avoid double slashes
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE}${cleanPath}`;
};

/**
 * Helper for making API requests with consistent configuration
 * @param endpoint - API endpoint path
 * @param options - Fetch options
 * @returns Promise with response
 */
export const apiRequest = async (
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> => {
  const url = api(endpoint);
  
  const defaultOptions: RequestInit = {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    credentials: "same-origin", // Include cookies if needed
  };

  try {
    const response = await fetch(url, { ...defaultOptions, ...options });
    
    // Log API calls in development
    if (process.env.NODE_ENV === "development") {
      console.log(`🌐 API Call: ${response.status} ${url}`);
    }
    
    // Handle non-2xx responses
    if (!response.ok) {
      const errorText = await response.text();
      console.error(`❌ API Error ${response.status}: ${url}`, errorText);
      throw new Error(`API Error ${response.status}: ${errorText}`);
    }
    
    return response;
  } catch (error) {
    console.error(`❌ API Error: ${url}`, error);
    throw error;
  }
};

/**
 * Helper for POST requests to API
 * @param endpoint - API endpoint path
 * @param data - Request body data
 * @param options - Additional fetch options
 * @returns Promise with response
 */
export const apiPost = async (
  endpoint: string,
  data: any,
  options: RequestInit = {}
): Promise<Response> => {
  return apiRequest(endpoint, {
    method: "POST",
    body: JSON.stringify(data),
    ...options,
  });
};

/**
 * Helper for GET requests to API
 * @param endpoint - API endpoint path
 * @param options - Additional fetch options
 * @returns Promise with response
 */
export const apiGet = async (
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> => {
  return apiRequest(endpoint, {
    method: "GET",
    ...options,
  });
};
