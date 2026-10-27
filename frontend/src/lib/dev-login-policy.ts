type DevelopmentLoginSettings = {
  nodeEnv: string | undefined;
  enabled: string | undefined;
  apiBaseUrl: string;
};

const loopbackHosts = new Set(["localhost", "127.0.0.1", "[::1]"]);
const loopbackAddresses = new Set(["127.0.0.1", "::1", "::ffff:127.0.0.1"]);

function localHttpUrl(value: string): URL | null {
  try {
    const url = new URL(value);
    return url.protocol === "http:" &&
      loopbackHosts.has(url.hostname) &&
      !url.username && !url.password &&
      url.pathname === "/" && !url.search && !url.hash
      ? url
      : null;
  } catch {
    return null;
  }
}

// Header checks are additional guards. The dev server must bind to loopback;
// forwarded headers alone cannot authenticate a machine or its owner.
export function allowsDevelopmentLogin(
  settings: DevelopmentLoginSettings,
  requestHeaders: Pick<Headers, "get">,
  requireOrigin = false,
): boolean {
  if (settings.nodeEnv !== "development" || settings.enabled !== "true") return false;
  if (!localHttpUrl(settings.apiBaseUrl)) return false;

  const host = requestHeaders.get("host");
  if (!host) return false;
  const pageUrl = localHttpUrl(`http://${host}`);
  if (!pageUrl || pageUrl.host !== host.toLowerCase()) return false;

  const forwardedHost = requestHeaders.get("x-forwarded-host");
  if (forwardedHost && forwardedHost.toLowerCase() !== pageUrl.host) return false;
  if (requestHeaders.get("forwarded")) return false;
  // Next.js populates x-forwarded-for from the socket for direct requests.
  const address = requestHeaders.get("x-forwarded-for");
  if (!address || !loopbackAddresses.has(address)) return false;
  const realIp = requestHeaders.get("x-real-ip");
  if (realIp && !loopbackAddresses.has(realIp)) return false;

  const origin = requestHeaders.get("origin");
  if (!origin) return !requireOrigin;
  return localHttpUrl(origin)?.origin === pageUrl.origin;
}
