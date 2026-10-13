export const voiceLabel = (v: string) => v.replace("_v", " v").replace("_", " ");

/** Channel clones first (OmniVoice), then Gemini voices. */
export function voiceGroups(voices: string[], channel: string[]) {
  return [
    { label: "Channel voices", items: voices.filter((v) => channel.includes(v)) },
    { label: "Gemini voices", items: voices.filter((v) => !channel.includes(v)) },
  ];
}
