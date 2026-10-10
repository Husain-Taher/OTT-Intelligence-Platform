import { handleAuth, handleLogin, handleLogout } from "@auth0/nextjs-auth0";
import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const DEV_BYPASS = process.env.AUTH_DISABLED === "true";
if (DEV_BYPASS && process.env.NODE_ENV === "production") {
  throw new Error("AUTH_DISABLED=true is not allowed in production builds");
}

const auth0Handler = handleAuth({
  login: handleLogin({
    authorizationParams: {
      audience: process.env.AUTH0_AUDIENCE,
      scope: "openid profile email",
    },
    returnTo: "/",
  }),
  signup: handleLogin({
    authorizationParams: {
      audience: process.env.AUTH0_AUDIENCE,
      scope: "openid profile email",
      screen_hint: "signup",
    },
    returnTo: "/",
  }),
  logout: handleLogout({ returnTo: "/" }),
});

/**
 * With AUTH_DISABLED=true (local UI work only) the sign-in endpoints are faked so the app
 * runs without an Auth0 tenant. The FastAPI side must also run with AUTH_DISABLED=true.
 */
export async function GET(req: NextRequest, ctx: { params: { auth0: string } }) {
  if (DEV_BYPASS) {
    const route = ctx.params.auth0;
    if (route === "me") {
      return NextResponse.json({ sub: "default_user", name: "Dev Pioneer", picture: null, email: "dev@localhost" });
    }
    return NextResponse.redirect(new URL("/", req.url));
  }
  return auth0Handler(req, ctx as any);
}
