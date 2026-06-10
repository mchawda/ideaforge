"use client";

import { ArrowUp, Mic, MicOff } from "lucide-react";
import { useCallback } from "react";
import { toast } from "sonner";

import { useVoiceInput } from "@/hooks/use-voice-input";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

type CommandBarProps = {
  mode: "ideabrowser" | "idea";
  onModeChange: (mode: "ideabrowser" | "idea") => void;
  ideaUrl: string;
  onIdeaUrlChange: (value: string) => void;
  ideaText: string;
  onIdeaTextChange: (value: string) => void;
  onSubmit: () => void;
  loading?: boolean;
};

const modes = [
  { id: "ideabrowser" as const, label: "IdeaBrowser URL" },
  { id: "idea" as const, label: "Your idea" },
];

const URL_PATTERN = /^https?:\/\//i;

export function CommandBar({
  mode,
  onModeChange,
  ideaUrl,
  onIdeaUrlChange,
  ideaText,
  onIdeaTextChange,
  onSubmit,
  loading = false,
}: CommandBarProps) {
  const handleTranscript = useCallback(
    (text: string, isFinal: boolean) => {
      if (!text) return;

      if (URL_PATTERN.test(text)) {
        onModeChange("ideabrowser");
        onIdeaUrlChange(text);
      } else {
        onModeChange("idea");
        onIdeaTextChange(isFinal ? text : text);
      }

      if (isFinal) {
        toast.message("Voice captured.");
      }
    },
    [onIdeaTextChange, onIdeaUrlChange, onModeChange],
  );

  const { supported, listening, recording, error, toggle } = useVoiceInput(handleTranscript);

  return (
    <div className="overflow-hidden rounded-2xl border-hairline border-border bg-card shadow-[0_24px_80px_-40px_rgba(0,0,0,0.8)]">
      <div className="px-5 pt-5 pb-4">
        {mode === "ideabrowser" ? (
          <Input
            id="idea-url"
            placeholder="Paste IdeaBrowser URL — https://ideabrowser.com/ideas/..."
            value={ideaUrl}
            onChange={(e) => onIdeaUrlChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") onSubmit();
            }}
            className="h-auto border-0 bg-transparent px-0 py-1 text-base shadow-none focus-visible:border-0 focus-visible:ring-0 md:text-[17px]"
          />
        ) : (
          <Textarea
            id="idea-text"
            placeholder="Describe the product you want to ship — or tap the mic"
            value={ideaText}
            onChange={(e) => onIdeaTextChange(e.target.value)}
            rows={3}
            className="min-h-24 resize-none border-0 bg-transparent px-0 py-1 text-base shadow-none focus-visible:border-0 focus-visible:ring-0 md:text-[17px]"
          />
        )}
        {listening && (
          <p className="mt-2 text-[13px] text-forge animate-forge-pulse">
            {recording ? "Recording… tap mic to stop" : "Listening…"}
          </p>
        )}
        {error && <p className="mt-2 text-[13px] text-destructive">{error}</p>}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-hairline border-border px-4 py-3">
        <div className="flex flex-wrap items-center gap-2">
          {modes.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onModeChange(item.id)}
              className={cn(
                "rounded-lg border-hairline px-3 py-1.5 text-[13px] font-medium transition-colors",
                mode === item.id
                  ? "border-forge/30 bg-forge-dim text-forge"
                  : "border-border bg-elevated text-muted-foreground hover:text-foreground",
              )}
            >
              {item.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          {supported && (
            <Button
              type="button"
              variant="outline"
              size="icon"
              className={cn(
                "size-9 shrink-0 rounded-full",
                listening && "border-forge/50 bg-forge-dim text-forge",
              )}
              onClick={toggle}
              aria-label={listening ? "Stop voice input" : "Start voice input"}
              aria-pressed={listening}
            >
              {listening ? <MicOff className="size-4" /> : <Mic className="size-4" />}
            </Button>
          )}
          <Button
            size="icon"
            className="size-9 shrink-0 rounded-full"
            onClick={onSubmit}
            disabled={loading}
            aria-label={loading ? "Starting build" : "Build this"}
          >
            <ArrowUp className="size-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
