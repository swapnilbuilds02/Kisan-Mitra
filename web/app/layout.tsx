import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "Kisan Mitra | Owner Console",
  description: "Kisan Mitra owner operations",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
