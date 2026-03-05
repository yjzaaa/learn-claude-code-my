import { RealtimeDemoClient } from "./client";

const locales = ["en", "zh", "ja"];

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export default function RealtimeDemoPage() {
  return <RealtimeDemoClient />;
}
