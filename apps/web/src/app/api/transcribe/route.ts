import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const apiKey =
    process.env.OPENAI_API_KEY?.trim() ||
    process.env.AI_GATEWAY_API_KEY?.trim();

  if (!apiKey) {
    return NextResponse.json(
      { error: "No transcription API key configured (OPENAI_API_KEY)." },
      { status: 503 },
    );
  }

  const form = await request.formData();
  const file = form.get("file");
  if (!(file instanceof Blob) || file.size === 0) {
    return NextResponse.json({ error: "Missing audio file." }, { status: 400 });
  }

  const body = new FormData();
  body.append("file", file, "voice.webm");
  body.append("model", "whisper-1");
  body.append("language", "en");

  const response = await fetch("https://api.openai.com/v1/audio/transcriptions", {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}` },
    body,
  });

  if (!response.ok) {
    const detail = (await response.text()).slice(0, 200);
    return NextResponse.json(
      { error: `Transcription failed: ${detail}` },
      { status: response.status },
    );
  }

  const data = (await response.json()) as { text?: string };
  return NextResponse.json({ text: (data.text ?? "").trim() });
}
