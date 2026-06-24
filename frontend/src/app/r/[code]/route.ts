import { NextRequest, NextResponse } from "next/server"
import { API_BASE as API } from "@/lib/api"

export async function GET(
  request: NextRequest,
  { params }: { params: { code: string } }
) {
  const { code } = params
  
  try {
    // Call backend redirect endpoint
    const res = await fetch(`${API}/api/v1/r/${code}`, {
      redirect: "manual",  // don't follow, capture redirect
      headers: {
        "X-Forwarded-For": request.headers.get("x-forwarded-for") || "",
        "User-Agent": request.headers.get("user-agent") || "",
        "Referer": request.headers.get("referer") || "",
      },
    })
    
    // Get the redirect location from backend
    const location = res.headers.get("location")
    if (location) {
      return NextResponse.redirect(location, { status: 302 })
    }
    
    // Fallback
    return NextResponse.redirect("https://bestpricetoday.vercel.app")
    
  } catch {
    return NextResponse.redirect("https://bestpricetoday.vercel.app")
  }
}
