import { ChatPageClient } from "./client";

const locales = ["en", "zh", "ja"];

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export default function ChatPage() {
  return <ChatPageClient />;
}
