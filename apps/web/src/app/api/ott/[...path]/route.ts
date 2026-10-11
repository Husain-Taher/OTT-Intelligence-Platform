import { getAccessToken, getSession } from "@auth0/nextjs-auth0";
import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const API = (process.env.OTT_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const DEV_BYPASS = process.env.AUTH_DISABLED === "true";

/**
 * Same-origin proxy to the FastAPI service. It attaches the user's Auth0 access token
 * server-side, so the token never reaches browser JavaScript.
 */
async function proxy(req: NextRequest, { params }: { params: { path: string[] } }) {
  const headers: Record<string, string> = { "Content-Type": req.headers.get("content-type") || "application/json" };

  if (!DEV_BYPASS) {
    try {
      const { accessToken } = await getAccessToken();
      if (!accessToken) throw new Error("no token");
      headers.Authorization = `Bearer ${accessToken}`;
      const user = (await getSession())?.user;
      if (user?.name) headers["x-user-name"] = encodeURIComponent(String(user.name));
      if (user?.email) headers["x-user-email"] = encodeURIComponent(String(user.email));
      if (user?.picture) headers["x-user-picture"] = encodeURIComponent(String(user.picture));
    } catch {
      return NextResponse.json({ detail: "Not signed in" }, { status: 401 });
    }
  }

  const url = `${API}/v1/${params.path.map(encodeURIComponent).join("/")}${req.nextUrl.search}`;
  const hasBody = !["GET", "HEAD"].includes(req.method);
  try {
    const upstream = await fetch(url, {
      method: req.method,
      headers,
      body: hasBody ? await req.text() : undefined,
      cache: "no-store",
    });
    if (!upstream.ok) {
      const errText = await upstream.clone().text().catch(() => "");
      console.warn(`[OTT Proxy Upstream ${upstream.status}] ${url}:`, errText.slice(0, 300));
    }
    return new NextResponse(upstream.body, {
      status: upstream.status,
      headers: { "Content-Type": upstream.headers.get("content-type") || "application/json" },
    });
  } catch (err: any) {
    console.error(`[OTT Proxy Error] Failed to fetch ${url}:`, err);
    return NextResponse.json({ 
      detail: `The recommendation service is not reachable (${API}). Error: ${err?.message || err}`,
      target_url: url
    }, { status: 502 });
  }
}

export { proxy as GET, proxy as POST, proxy as DELETE };
